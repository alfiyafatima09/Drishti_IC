"""
Datasheet download service.
Multi-provider architecture for downloading datasheets from various manufacturers.
Supports: STM, Texas Instruments (TI), and extensible for more.
"""
import logging
import httpx
from pathlib import Path
from typing import Tuple, Optional, Dict, Type
from datetime import datetime
from abc import ABC, abstractmethod

from backend.core.config import settings

logger = logging.getLogger(__name__)


class DatasheetDownloadException(Exception):
    """Exception raised when datasheet download fails."""
    pass


class UnsupportedManufacturerException(Exception):
    """Exception raised when manufacturer is not supported."""
    pass


class DatasheetProvider(ABC):
    """Abstract base class for datasheet providers."""
    
    def __init__(self, datasheet_root: Path):
        """Initialize the provider with storage path."""
        self.datasheet_root = datasheet_root
        self.datasheet_root.mkdir(parents=True, exist_ok=True)
    
    @abstractmethod
    def construct_url(self, ic_id: str) -> str:
        """Construct the download URL for the IC datasheet."""
        pass
    
    @abstractmethod
    def get_manufacturer_name(self) -> str:
        """Get the manufacturer name."""
        pass
    
    def get_local_path(self, ic_id: str, manufacturer: str) -> Path:
        """
        Get the local file path for storing the datasheet.
        Organized by manufacturer folders.
        
        Args:
            ic_id: IC identifier
            manufacturer: Manufacturer name
            
        Returns:
            Path object for the local file
        """
        ic_id_clean = ic_id.lower().strip()
        manufacturer_clean = manufacturer.lower().strip()
        
        # Create manufacturer subfolder
        manufacturer_folder = self.datasheet_root / manufacturer_clean
        manufacturer_folder.mkdir(parents=True, exist_ok=True)
        
        return manufacturer_folder / f"{ic_id_clean}.pdf"
    
    async def download(self, ic_id: str) -> Tuple[Path, int]:
        """
        Download datasheet and save locally.
        
        Args:
            ic_id: IC identifier
            
        Returns:
            Tuple of (file_path, file_size_bytes)
            
        Raises:
            DatasheetDownloadException: If download fails
        """
        url = self.construct_url(ic_id)
        local_path = self.get_local_path(ic_id, self.get_manufacturer_name())
        
        logger.info(f"Downloading {self.get_manufacturer_name()} datasheet for {ic_id} from {url}")
        
        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                response = await client.get(url)
                
                if response.status_code == 404:
                    raise DatasheetDownloadException(
                        f"Datasheet not found for IC '{ic_id}' from {self.get_manufacturer_name()}. "
                        f"The URL {url} returned 404."
                    )
                
                if response.status_code != 200:
                    raise DatasheetDownloadException(
                        f"Failed to download datasheet. HTTP {response.status_code}"
                    )
                
                # Verify content type is PDF
                content_type = response.headers.get("content-type", "")
                if "pdf" not in content_type.lower() and "application/octet-stream" not in content_type.lower():
                    raise DatasheetDownloadException(
                        f"Downloaded file is not a PDF. Content-Type: {content_type}"
                    )
                
                # Save the file
                with local_path.open("wb") as f:
                    f.write(response.content)
                
                file_size = len(response.content)
                logger.info(
                    f"Successfully downloaded {self.get_manufacturer_name()} datasheet for {ic_id}. "
                    f"Size: {file_size} bytes. Saved to: {local_path}"
                )
                
                return local_path, file_size
                
        except httpx.TimeoutException as e:
            logger.error(f"Timeout while downloading datasheet for {ic_id}: {e}")
            raise DatasheetDownloadException(
                f"Download timeout for IC '{ic_id}'. Please try again."
            )
        except httpx.RequestError as e:
            logger.error(f"Network error while downloading datasheet for {ic_id}: {e}")
            raise DatasheetDownloadException(
                f"Network error while downloading datasheet for '{ic_id}': {str(e)}"
            )
        except OSError as e:
            logger.error(f"File system error while saving datasheet for {ic_id}: {e}")
            raise DatasheetDownloadException(
                f"Failed to save datasheet for '{ic_id}': {str(e)}"
            )


class STMProvider(DatasheetProvider):
    """STMicroelectronics datasheet provider."""
    
    BASE_URL = "https://www.st.com/resource/en/datasheet"
    
    def construct_url(self, ic_id: str) -> str:
        """
        Construct the STM datasheet download URL.
        Format: https://www.st.com/resource/en/datasheet/{ic_id}.pdf
        
        Args:
            ic_id: IC identifier (e.g., 'stm32l031k6')
            
        Returns:
            Full URL to the datasheet PDF
        """
        ic_id_clean = ic_id.lower().strip()
        return f"{self.BASE_URL}/{ic_id_clean}.pdf"
    
    def get_manufacturer_name(self) -> str:
        """Get manufacturer name."""
        return "STM"


class TIProvider(DatasheetProvider):
    """Texas Instruments datasheet provider."""
    
    BASE_URL = "https://www.ti.com/lit/ds/symlink"
    
    def construct_url(self, ic_id: str) -> str:
        """
        Construct the TI datasheet download URL.
        Format: https://www.ti.com/lit/ds/symlink/{ic_id}.pdf
        
        Args:
            ic_id: IC identifier (e.g., 'lm358', 'lm555')
            
        Returns:
            Full URL to the datasheet PDF
        """
        ic_id_clean = ic_id.lower().strip()
        return f"{self.BASE_URL}/{ic_id_clean}.pdf"
    
    def get_manufacturer_name(self) -> str:
        """Get manufacturer name."""
        return "TI"


class DatasheetService:
    """Service for downloading and managing IC datasheets with multi-provider support."""
    
    # Registry of supported manufacturers
    PROVIDERS: Dict[str, Type[DatasheetProvider]] = {
        "STM": STMProvider,
        "TI": TIProvider,
    }
    
    def __init__(self):
        """Initialize the datasheet service."""
        self.datasheet_root = settings.DATASHEET_ROOT
        self.datasheet_root.mkdir(parents=True, exist_ok=True)
        self._provider_instances: Dict[str, DatasheetProvider] = {}
    
    def get_provider(self, manufacturer: str) -> DatasheetProvider:
        """
        Get or create a provider instance for the given manufacturer.
        
        Args:
            manufacturer: Manufacturer name (e.g., 'STM', 'TI')
            
        Returns:
            Provider instance
            
        Raises:
            UnsupportedManufacturerException: If manufacturer is not supported
        """
        manufacturer_upper = manufacturer.upper().strip()
        
        if manufacturer_upper not in self.PROVIDERS:
            supported = ", ".join(self.PROVIDERS.keys())
            raise UnsupportedManufacturerException(
                f"Manufacturer '{manufacturer}' is not supported. "
                f"Supported manufacturers: {supported}"
            )
        
        # Create provider instance if not already cached
        if manufacturer_upper not in self._provider_instances:
            provider_class = self.PROVIDERS[manufacturer_upper]
            self._provider_instances[manufacturer_upper] = provider_class(self.datasheet_root)
        
        return self._provider_instances[manufacturer_upper]
    
    def get_local_path(self, ic_id: str, manufacturer: str) -> Path:
        """
        Get the local file path for storing the datasheet.
        
        Args:
            ic_id: IC identifier
            manufacturer: Manufacturer name
            
        Returns:
            Path object for the local file
        """
        provider = self.get_provider(manufacturer)
        return provider.get_local_path(ic_id, manufacturer)
    
    async def download_datasheet(self, ic_id: str, manufacturer: str) -> Tuple[Path, int]:
        """
        Download datasheet from the appropriate manufacturer and save locally.
        
        Args:
            ic_id: IC identifier (e.g., 'stm32l031k6', 'lm358')
            manufacturer: Manufacturer name (e.g., 'STM', 'TI')
            
        Returns:
            Tuple of (file_path, file_size_bytes)
            
        Raises:
            DatasheetDownloadException: If download fails
            UnsupportedManufacturerException: If manufacturer is not supported
        """
        provider = self.get_provider(manufacturer)
        return await provider.download(ic_id)
    
    def datasheet_exists(self, ic_id: str, manufacturer: str) -> bool:
        """
        Check if datasheet already exists locally.
        
        Args:
            ic_id: IC identifier
            manufacturer: Manufacturer name
            
        Returns:
            True if datasheet exists, False otherwise
        """
        try:
            local_path = self.get_local_path(ic_id, manufacturer)
            return local_path.exists()
        except UnsupportedManufacturerException:
            return False
    
    def get_datasheet_info(self, ic_id: str, manufacturer: str) -> Optional[dict]:
        """
        Get information about locally stored datasheet.
        
        Args:
            ic_id: IC identifier
            manufacturer: Manufacturer name
            
        Returns:
            Dictionary with file info or None if not found
        """
        try:
            local_path = self.get_local_path(ic_id, manufacturer)
            if not local_path.exists():
                return None
            
            stat = local_path.stat()
            return {
                "file_path": str(local_path),
                "file_size_bytes": stat.st_size,
                "modified_at": datetime.fromtimestamp(stat.st_mtime)
            }
        except UnsupportedManufacturerException:
            return None
    
    @staticmethod
    def get_supported_manufacturers() -> list[str]:
        """
        Get list of supported manufacturers.
        
        Returns:
            List of manufacturer names
        """
        return list(DatasheetService.PROVIDERS.keys())


# Global instance
datasheet_service = DatasheetService()
