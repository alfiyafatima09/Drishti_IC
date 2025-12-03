"""
Main datasheet service.
Orchestrates downloading, extraction, and storage of IC datasheets.
"""
import logging
import asyncio
from pathlib import Path
from typing import Tuple, Optional, Dict, List

from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.constants import (
    Manufacturer,
    get_supported_manufacturers,
    get_manufacturer_name,
    get_manufacturer_url_pattern,
    is_valid_manufacturer,
    DatasheetDownloadStatus,
    ICSource,
)
from .exceptions import (
    DatasheetDownloadException,
    UnsupportedManufacturerException,
)
from .providers import PROVIDERS
from .providers.base import DatasheetProvider
from .extractors import EXTRACTORS
from .extractors.base import DatasheetExtractor
from .storage import (
    get_datasheet_path_from_db,
    store_ic_specification,
    store_multiple_ic_specifications,
)
from .downloader import generate_hash

logger = logging.getLogger(__name__)


class DatasheetService:
    """Service for downloading and managing IC datasheets with multi-provider support."""
    
    def __init__(self):
        """Initialize the datasheet service."""
        self.datasheet_root = settings.DATASHEET_FOLDER
        self.datasheet_root.mkdir(parents=True, exist_ok=True)
        self._provider_instances: Dict[str, DatasheetProvider] = {}
        self._extractor_instances: Dict[str, DatasheetExtractor] = {}
    
    def _get_provider(self, manufacturer_code: str) -> DatasheetProvider:
        """
        Get or create a provider instance for the given manufacturer.
        
        Args:
            manufacturer_code: Manufacturer enum code (e.g., 'STM', 'TI')
            
        Returns:
            Provider instance
            
        Raises:
            UnsupportedManufacturerException: If manufacturer is not supported
        """
        manufacturer_code = manufacturer_code.upper().strip()
        
        if not is_valid_manufacturer(manufacturer_code):
            supported = ", ".join(get_supported_manufacturers())
            raise UnsupportedManufacturerException(
                f"Manufacturer '{manufacturer_code}' is not supported. "
                f"Supported manufacturers: {supported}"
            )
        
        if manufacturer_code not in self._provider_instances:
            from .providers import PROVIDERS
            provider_class = PROVIDERS[manufacturer_code]
            self._provider_instances[manufacturer_code] = provider_class(
                self.datasheet_root,
                manufacturer_code
            )
        
        return self._provider_instances[manufacturer_code]
    
    def _get_extractor(self, manufacturer_code: str) -> DatasheetExtractor:
        """
        Get or create an extractor instance for the given manufacturer.
        
        Args:
            manufacturer_code: Manufacturer enum code (e.g., 'STM', 'TI')
            
        Returns:
            Extractor instance
        """
        manufacturer_code = manufacturer_code.upper().strip()
        
        if manufacturer_code not in self._extractor_instances:
            from .extractors import EXTRACTORS
            extractor_class = EXTRACTORS.get(manufacturer_code)
            if extractor_class:
                self._extractor_instances[manufacturer_code] = extractor_class(manufacturer_code)
            else:
                from .extractors.base import DatasheetExtractor
                self._extractor_instances[manufacturer_code] = DatasheetExtractor(manufacturer_code)
        
        return self._extractor_instances[manufacturer_code]
    
    async def get_local_path_from_db(
        self,
        part_number: str,
        manufacturer_code: str,
        db: Optional[AsyncSession] = None
    ) -> Optional[str]:
        """
        Get datasheet_path from database if it exists.
        
        Args:
            part_number: IC part number
            manufacturer_code: Manufacturer enum code
            db: Database session
            
        Returns:
            datasheet_path from database, or None if not found
        """
        if not db:
            return None
        return await get_datasheet_path_from_db(db, part_number, manufacturer_code)
    
    def get_local_path(
        self,
        part_number: str,
        manufacturer_code: str,
        hash_value: Optional[str] = None
    ) -> Path:
        """
        Get the local file path for storing the datasheet.
        Uses hash-based filename: datasheets/{manufacturer}/{hash}.pdf
        
        Args:
            part_number: IC part number (used to generate hash if not provided)
            manufacturer_code: Manufacturer enum code
            hash_value: Optional pre-generated hash (if None, generates from part_number)
            
        Returns:
            Path object for the local file
        """
        provider = self._get_provider(manufacturer_code)
        return provider.get_local_path(part_number, hash_value)
    
    async def _download_single(
        self,
        part_number: str,
        manufacturer_code: str,
        db: Optional[AsyncSession] = None
    ) -> Dict:
        """
        Download datasheet from a single manufacturer.
        Checks database first for existing path, otherwise generates hash.
        
        Args:
            part_number: IC part number
            manufacturer_code: Manufacturer enum code
            db: Optional database session to check for existing path
            
        Returns:
            Dictionary with download result including hash and path
        """
        try:
            # Check database first for existing datasheet_path
            existing_path = await self.get_local_path_from_db(part_number, manufacturer_code, db)
            
            provider = self._get_provider(manufacturer_code)
            
            if existing_path:
                # Use existing path from database
                # Reconstruct full path from relative path stored in DB
                if Path(existing_path).is_absolute():
                    file_path = Path(existing_path)
                else:
                    # Relative path: reconstruct from project root or datasheet_root
                    if existing_path.startswith("datasheets/"):
                        file_path = Path(existing_path)
                    else:
                        file_path = self.datasheet_root / existing_path
                
                # Check if file exists
                if file_path.exists():
                    logger.info(
                        f"Using existing datasheet from database: {existing_path} "
                        f"for {part_number} from {manufacturer_code}"
                    )
                    file_size = file_path.stat().st_size
                    datasheet_url = provider.construct_url(part_number)
                    hash_value = file_path.stem
                    
                    return {
                        "manufacturer": manufacturer_code,
                        "manufacturer_name": get_manufacturer_name(manufacturer_code),
                        "status": DatasheetDownloadStatus.SUCCESS.value,
                        "file_path": existing_path,
                        "file_size_bytes": file_size,
                        "datasheet_url": datasheet_url,
                        "hash_value": hash_value,
                        "data_extracted": False,
                        "extracted_ics": [],
                        "error": None,
                    }
                else:
                    logger.warning(
                        f"Datasheet path in database ({existing_path}) does not exist, "
                        f"will download new copy for {part_number} from {manufacturer_code}"
                    )
            
            # No existing path in DB, download and generate hash
            file_path, file_size, datasheet_url, hash_value = await provider.download(part_number)
            
            # Convert to relative path for storage in database
            relative_path = f"datasheets/{manufacturer_code.lower()}/{hash_value}.pdf"
            
            # Extract data from PDF
            data_extracted = False
            extracted_ics = []
            try:
                extractor = self._get_extractor(manufacturer_code)
                extracted_ics = extractor.extract(file_path)
                data_extracted = len(extracted_ics) > 0
                if data_extracted:
                    logger.info(
                        f"Extracted {len(extracted_ics)} IC variants from PDF: {file_path}"
                    )
            except Exception as e:
                logger.warning(f"Failed to extract data from PDF {file_path}: {e}")
                # Continue even if extraction fails - we still have the PDF
            
            return {
                "manufacturer": manufacturer_code,
                "manufacturer_name": get_manufacturer_name(manufacturer_code),
                "status": DatasheetDownloadStatus.SUCCESS.value,
                "file_path": relative_path,
                "file_size_bytes": file_size,
                "datasheet_url": datasheet_url,
                "hash_value": hash_value,
                "data_extracted": data_extracted,
                "extracted_ics": extracted_ics,  # List of IC variants found
                "error": None,
            }
        except DatasheetDownloadException as e:
            error_msg = str(e)
            status = DatasheetDownloadStatus.NOT_FOUND if "404" in error_msg or "not found" in error_msg.lower() else (
                DatasheetDownloadStatus.TIMEOUT if "timeout" in error_msg.lower() else DatasheetDownloadStatus.ERROR
            )
            
            return {
                "manufacturer": manufacturer_code,
                "manufacturer_name": get_manufacturer_name(manufacturer_code),
                "status": status.value,
                "file_path": None,
                "file_size_bytes": None,
                "datasheet_url": get_manufacturer_url_pattern(manufacturer_code).format(ic_id=part_number.lower()),
                "data_extracted": False,
                "extracted_ics": [],
                "error": error_msg,
            }
        except Exception as e:
            logger.exception(f"Unexpected error downloading from {manufacturer_code}: {e}")
            return {
                "manufacturer": manufacturer_code,
                "manufacturer_name": get_manufacturer_name(manufacturer_code),
                "status": DatasheetDownloadStatus.ERROR.value,
                "file_path": None,
                "file_size_bytes": None,
                "datasheet_url": get_manufacturer_url_pattern(manufacturer_code).format(ic_id=part_number.lower()),
                "data_extracted": False,
                "extracted_ics": [],
                "error": str(e),
            }
    
    async def download_datasheet(
        self,
        part_number: str,
        manufacturer_code: Optional[str] = None,
        db: Optional[AsyncSession] = None
    ) -> Dict:
        """
        Download datasheet from manufacturer(s) and store in database.
        
        If manufacturer_code is provided, downloads only from that manufacturer.
        If omitted, tries ALL supported manufacturers in parallel.
        
        Args:
            part_number: IC part number
            manufacturer_code: Optional manufacturer enum code
            db: Optional database session for storing extracted data
            
        Returns:
            Dictionary matching DatasheetDownloadResponse schema
        """
        part_number = part_number.strip()
        
        # Determine which manufacturers to try
        if manufacturer_code:
            if not is_valid_manufacturer(manufacturer_code):
                raise UnsupportedManufacturerException(
                    f"Invalid manufacturer: {manufacturer_code}"
                )
            manufacturers_to_try = [manufacturer_code.upper()]
        else:
            manufacturers_to_try = get_supported_manufacturers()
        
        logger.info(
            f"Downloading datasheet for {part_number} from manufacturers: {manufacturers_to_try}"
        )
        
        # Download from all manufacturers in parallel
        download_tasks = [
            self._download_single(part_number, mfr, db)
            for mfr in manufacturers_to_try
        ]
        results = await asyncio.gather(*download_tasks)
        
        # Process results
        manufacturers_found = [
            r["manufacturer"] for r in results
            if r["status"] == DatasheetDownloadStatus.SUCCESS.value
        ]
        manufacturers_failed = [
            r["manufacturer"] for r in results
            if r["status"] != DatasheetDownloadStatus.SUCCESS.value
        ]
        
        # Store successful downloads in database
        database_entries_created = 0
        if db:
            for result in results:
                if result["status"] == DatasheetDownloadStatus.SUCCESS.value:
                    mfr_code = result["manufacturer"]
                    source_map = {
                        Manufacturer.STM: ICSource.SCRAPED_STM,
                        Manufacturer.TI: ICSource.SCRAPED_TI,
                    }
                    source = source_map.get(mfr_code, ICSource.MANUAL)
                    
                    # Check if we extracted IC data from PDF
                    extracted_ics = result.get("extracted_ics", [])
                    
                    if extracted_ics:
                        # Store all extracted IC variants
                        stored_count = await store_multiple_ic_specifications(
                            db=db,
                            ic_specs=extracted_ics,
                            manufacturer_code=mfr_code,
                            datasheet_url=result["datasheet_url"],
                            datasheet_path=result["file_path"],
                            source=source
                        )
                        database_entries_created += stored_count
                        if stored_count > 0:
                            logger.debug(f"Stored {stored_count} IC variants from PDF for {part_number} from {mfr_code}")
                    else:
                        # No extraction data, store basic entry with requested part_number
                        success = await store_ic_specification(
                            db=db,
                            part_number=part_number,
                            manufacturer_code=mfr_code,
                            datasheet_url=result["datasheet_url"],
                            datasheet_path=result["file_path"],
                            source=source
                        )
                        if success:
                            database_entries_created += 1
        
        # Build response message
        if manufacturers_found:
            if len(manufacturers_found) == 1:
                message = f"Successfully downloaded and processed datasheet from {get_manufacturer_name(manufacturers_found[0])}"
            else:
                message = f"Found datasheet from {len(manufacturers_found)} manufacturers"
            if manufacturers_failed:
                message += f", {len(manufacturers_failed)} failed"
        else:
            message = f"No datasheet found for '{part_number}' on any supported manufacturer"
        
        return {
            "success": len(manufacturers_found) > 0,
            "part_number": part_number,
            "manufacturers_found": manufacturers_found,
            "manufacturers_tried": manufacturers_to_try,
            "manufacturers_failed": manufacturers_failed,
            "results": results,
            "database_entries_created": database_entries_created,
            "message": message,
        }
    
    def datasheet_exists(self, part_number: str, manufacturer_code: str) -> bool:
        """
        Check if datasheet already exists locally.
        
        Args:
            part_number: IC part number
            manufacturer_code: Manufacturer enum code
            
        Returns:
            True if datasheet exists, False otherwise
        """
        try:
            local_path = self.get_local_path(part_number, manufacturer_code)
            return local_path.exists()
        except UnsupportedManufacturerException:
            return False
    
    @staticmethod
    def get_supported_manufacturers() -> List[str]:
        """Get list of supported manufacturer codes."""
        return get_supported_manufacturers()
    
    @staticmethod
    def get_manufacturer_details() -> Dict:
        """Get detailed information about all supported manufacturers."""
        from core.constants import get_manufacturer_details
        return get_manufacturer_details()


# Global instance
datasheet_service = DatasheetService()

