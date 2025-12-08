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
from services.datasheet_storage import (
    generate_hash,
    get_storage_folder,
    get_datasheet_filename,
    get_datasheet_path,
    datasheet_exists,
)
from .exceptions import (
    DatasheetDownloadException,
    UnsupportedManufacturerException,
)
from .providers import PROVIDERS, DatasheetProvider
from .extractors import EXTRACTORS
from .extractors.base import DatasheetExtractor
from .storage import (
    get_datasheet_path_from_db,
    store_ic_specification,
    store_multiple_ic_specifications,
)

logger = logging.getLogger(__name__)


class DatasheetService:
    """Service for downloading and managing IC datasheets with multi-provider support."""
    
    def __init__(self):
        """Initialize the datasheet service."""
        self.datasheet_root = get_storage_folder()
        self._provider_instances: Dict[str, DatasheetProvider] = {}
        self._extractor_instances: Dict[str, DatasheetExtractor] = {}
    
    def _get_provider(self, manufacturer_code: str) -> DatasheetProvider:
        """Get or create a provider instance for the given manufacturer."""
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
        """Get or create an extractor instance for the given manufacturer."""
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
        """Get datasheet_path from database if it exists."""
        if not db:
            return None
        return await get_datasheet_path_from_db(db, part_number, manufacturer_code)
    
    def get_local_path(
        self,
        part_number: str,
        manufacturer_code: str,
        hash_value: Optional[str] = None
    ) -> Path:
        """Get the local file path for storing the datasheet."""
        if hash_value is None:
            hash_value = generate_hash(part_number, manufacturer_code)
        return self.datasheet_root / f"{hash_value}.pdf"
    
    async def _download_single(
        self,
        part_number: str,
        manufacturer_code: str,
        db: Optional[AsyncSession] = None
    ) -> Dict:
        """Download datasheet from a single manufacturer."""
        try:
            # Check if we already have this datasheet
            existing_path = await self.get_local_path_from_db(part_number, manufacturer_code, db)
            
            provider = self._get_provider(manufacturer_code)
            
            if existing_path:
                # Resolve the path using unified storage
                try:
                    file_path = get_datasheet_path(existing_path)
                    if file_path.exists():
                        logger.info(
                            f"Using existing datasheet: {existing_path} "
                            f"for {part_number} from {manufacturer_code}"
                        )
                        file_size = file_path.stat().st_size
                        datasheet_url = provider.construct_url(part_number)
                        
                        return {
                            "manufacturer": manufacturer_code,
                            "manufacturer_name": get_manufacturer_name(manufacturer_code),
                            "status": DatasheetDownloadStatus.SUCCESS.value,
                            "file_path": existing_path,  # Keep original DB value
                            "file_size_bytes": file_size,
                            "datasheet_url": datasheet_url,
                            "hash_value": file_path.stem,
                            "data_extracted": False,
                            "extracted_ics": [],
                            "error": None,
                        }
                except Exception as e:
                    logger.warning(f"Could not resolve existing path {existing_path}: {e}")
            
            # Download new datasheet
            file_path, file_size, datasheet_url, hash_value = await provider.download(part_number)
            
            # Store just the filename in DB
            filename = f"{hash_value}.pdf"
            
            # Try to extract data from PDF
            data_extracted = False
            extracted_ics = []
            try:
                extractor = self._get_extractor(manufacturer_code)
                extracted_ics = extractor.extract(file_path)
                data_extracted = len(extracted_ics) > 0
                if data_extracted:
                    logger.info(f"Extracted {len(extracted_ics)} IC variants from PDF: {file_path}")
            except Exception as e:
                logger.warning(f"Failed to extract data from PDF {file_path}: {e}")
            
            return {
                "manufacturer": manufacturer_code,
                "manufacturer_name": get_manufacturer_name(manufacturer_code),
                "status": DatasheetDownloadStatus.SUCCESS.value,
                "file_path": filename,  # Store just filename
                "file_size_bytes": file_size,
                "datasheet_url": datasheet_url,
                "hash_value": hash_value,
                "data_extracted": data_extracted,
                "extracted_ics": extracted_ics,
                "error": None,
            }
        except DatasheetDownloadException as e:
            error_msg = str(e)
            status = DatasheetDownloadStatus.NOT_FOUND if "404" in error_msg or "not found" in error_msg.lower() else (
                DatasheetDownloadStatus.TIMEOUT if "timeout" in error_msg.lower() else DatasheetDownloadStatus.ERROR
            )
            # Simple one-line log for expected errors (404, timeout)
            logger.debug(f"{manufacturer_code}: {error_msg}")
            
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
            error_msg = str(e)
            # Classify common errors and log appropriately (no stack trace for expected errors)
            if "404" in error_msg or "not found" in error_msg.lower():
                logger.debug(f"{manufacturer_code}: Not found (404)")
                status = DatasheetDownloadStatus.NOT_FOUND
            elif "timeout" in error_msg.lower() or "ReadTimeout" in type(e).__name__:
                logger.debug(f"{manufacturer_code}: Timeout")
                status = DatasheetDownloadStatus.TIMEOUT
            else:
                # Only log full exception for truly unexpected errors
                logger.warning(f"{manufacturer_code}: {error_msg}")
                status = DatasheetDownloadStatus.ERROR
            
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
    
    async def download_datasheet(
        self,
        part_number: str,
        manufacturer_code: Optional[str] = None,
        db: Optional[AsyncSession] = None
    ) -> Dict:
        """
        Download datasheet from manufacturer(s) and store in database.
        
        If manufacturer_code is provided, downloads only from that manufacturer.
        If omitted, tries manufacturers SEQUENTIALLY (one-by-one) and stops on first success.
        """
        part_number = part_number.strip()
        
        if manufacturer_code:
            if not is_valid_manufacturer(manufacturer_code):
                raise UnsupportedManufacturerException(f"Invalid manufacturer: {manufacturer_code}")
            manufacturers_to_try = [manufacturer_code.upper()]
        else:   
            manufacturers_to_try = get_supported_manufacturers()
        
        logger.info(f"Downloading datasheet for {part_number} from manufacturers (sequential): {manufacturers_to_try}")
        
        # Try manufacturers one-by-one, stop on first success
        results = []
        successful_result = None
        
        for mfr in manufacturers_to_try:
            logger.info(f"Trying {mfr} for {part_number}...")
            result = await self._download_single(part_number, mfr, db)
            results.append(result)
            
            if result["status"] == DatasheetDownloadStatus.SUCCESS.value:
                logger.info(f"SUCCESS: Found datasheet for {part_number} on {mfr}")
                successful_result = result
                break  # Stop on first success
            else:
                logger.info(f"FAILED: {mfr} - {result.get('error', 'Not found')}")
        
        manufacturers_found = [
            r["manufacturer"] for r in results
            if r["status"] == DatasheetDownloadStatus.SUCCESS.value
        ]
        manufacturers_failed = [
            r["manufacturer"] for r in results
            if r["status"] != DatasheetDownloadStatus.SUCCESS.value
        ]
        
        # Store results in database (only the successful one)
        database_entries_created = 0
        if db and successful_result:
            result = successful_result
            mfr_code = result["manufacturer"]
            source_map = {
                Manufacturer.STM: ICSource.SCRAPED_STM,
                Manufacturer.TI: ICSource.SCRAPED_TI,
                Manufacturer.INFINEON: ICSource.SCRAPED_INFINEON,
            }
            source = source_map.get(mfr_code, ICSource.MANUAL)
            
            extracted_ics = result.get("extracted_ics", [])
            
            if extracted_ics:
                stored_count = await store_multiple_ic_specifications(
                    db=db,
                    ic_specs=extracted_ics,
                    manufacturer_code=mfr_code,
                    datasheet_url=result["datasheet_url"],
                    datasheet_path=result["file_path"],
                    source=source
                )
                database_entries_created += stored_count
            else:   
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
        
        # Try DigiKey fallback if no manufacturer-specific datasheet found
        digikey_result = None
        if not manufacturers_found:
            logger.info(f"No manufacturer found for {part_number}, trying DigiKey fallback...")
            digikey_result = await self._try_digikey_fallback(part_number, db)
            
            if digikey_result and digikey_result.get("success"):
                manufacturers_found = ["DIGIKEY"]
                database_entries_created += digikey_result.get("saved_to_db", 0)
                results.append({
                    "manufacturer": "DIGIKEY",
                    "manufacturer_name": "DigiKey (Fallback)",
                    "status": DatasheetDownloadStatus.SUCCESS.value,
                    "file_path": digikey_result.get("filename"),
                    "file_size_bytes": None,
                    "datasheet_url": None,
                    "data_extracted": digikey_result.get("total_variants", 0) > 0,
                    "extracted_ics": digikey_result.get("ic_variants", []),
                    "error": None,
                })
        
        # Build response message
        if manufacturers_found:
            if "DIGIKEY" in manufacturers_found:
                message = f"Found datasheet via DigiKey fallback for '{part_number}'"
            elif len(manufacturers_found) == 1:
                message = f"Successfully downloaded and processed datasheet from {get_manufacturer_name(manufacturers_found[0])}"
            else:
                message = f"Found datasheet from {len(manufacturers_found)} manufacturers"
            if manufacturers_failed:
                message += f", {len(manufacturers_failed)} failed"
        else:
            message = f"No datasheet found for '{part_number}' on any supported manufacturer or DigiKey"
        
        return {
            "success": len(manufacturers_found) > 0,
            "part_number": part_number,
            "manufacturers_found": manufacturers_found,
            "manufacturers_tried": manufacturers_to_try + (["DIGIKEY"] if digikey_result else []),
            "manufacturers_failed": manufacturers_failed,
            "results": results,
            "database_entries_created": database_entries_created,
            "message": message,
        }
    
    async def _try_digikey_fallback(
        self,
        part_number: str,
        db: Optional[AsyncSession] = None
    ) -> Optional[Dict]:
        """Try DigiKey as fallback when no manufacturer-specific datasheet is found."""
        try:
            from services.digikey import digi_service, DigiKeyException
            from services.pdf_parser import parse_pdf
            from services.datasheet_storage import normalize_manufacturer
            
            logger.info(f"Trying DigiKey fallback for {part_number}")
            
            search_response = digi_service.search_keyword(part_number)
            
            datasheet_info = digi_service.extract_first_datasheet_info(search_response)
            if not datasheet_info:
                logger.warning(f"DigiKey: No datasheet URL found for {part_number}")
                return None
            
            datasheet_url = datasheet_info["url"]
            manufacturer = datasheet_info.get("manufacturer", "Unknown")
            digikey_part_number = datasheet_info.get("part_number") or part_number
            
            # Download using unified storage
            filename = digi_service.download_pdf(
                url=datasheet_url,
                part_number=digikey_part_number,
                manufacturer=manufacturer
            )
            
            logger.info(f"DigiKey: Downloaded PDF as {filename}")
            
            # Parse the PDF
            local_path = get_datasheet_path(filename)
            parsed = parse_pdf(local_path, manufacturer=manufacturer)
            
            ic_variants = parsed.get("ic_variants", [])
            saved_count = 0
            
            if db and ic_variants:
                from api.endpoints.digikey import save_variants_to_db
                saved_count = await save_variants_to_db(
                    db=db,
                    variants=ic_variants,
                    datasheet_url=datasheet_url,
                    datasheet_path=filename
                )
                logger.info(f"DigiKey: Saved {saved_count} variants to database")
            elif db and not ic_variants:
                manufacturer_code = normalize_manufacturer(manufacturer)
                
                basic_variant = {
                    "part_number": digikey_part_number.upper(),
                    "manufacturer": manufacturer_code,
                    "pin_count": 0,
                    "package_type": None,
                    "description": f"{manufacturer} {digikey_part_number}",
                }
                
                from api.endpoints.digikey import save_variants_to_db
                saved_count = await save_variants_to_db(
                    db=db,
                    variants=[basic_variant],
                    datasheet_url=datasheet_url,
                    datasheet_path=filename
                )
            
            return {
                "success": True,
                "filename": filename,
                "manufacturer": manufacturer,
                "total_variants": len(ic_variants),
                "ic_variants": ic_variants,
                "saved_to_db": saved_count,
            }
            
        except Exception as e:
            logger.warning(f"DigiKey fallback failed for {part_number}: {e}")
            return None
    
    def datasheet_exists(self, part_number: str, manufacturer_code: str) -> bool:
        """Check if datasheet already exists locally."""
        return datasheet_exists(part_number, manufacturer_code)
    
    @staticmethod
    def get_supported_manufacturers() -> List[str]:
        """Get list of supported manufacturer codes."""
        return get_supported_manufacturers()
    
    @staticmethod
    def get_manufacturer_details() -> Dict:
        """Get detailed information about all supported manufacturers."""
        from core.constants import get_manufacturer_details
        return get_manufacturer_details()


datasheet_service = DatasheetService()
