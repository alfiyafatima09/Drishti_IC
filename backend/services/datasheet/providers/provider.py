"""
Datasheet provider base class.
Uses unified storage module for consistent PDF storage.
"""
from pathlib import Path
from typing import Tuple, Optional

from core.constants import (
    Manufacturer,
    get_manufacturer_name,
    MANUFACTURER_URL_PATTERNS,
    is_valid_manufacturer,
)
from core.config import settings
from services.datasheet_storage import (
    generate_hash,
    get_storage_folder,
    get_datasheet_filename,
    download_pdf_async,
)


def construct_datasheet_url(manufacturer_code: str, part_number: str) -> str:
    """Construct the datasheet URL for a given manufacturer and part number."""
    manufacturer_code = manufacturer_code.upper().strip()
    
    if not is_valid_manufacturer(manufacturer_code):
        raise ValueError(f"Unsupported manufacturer: {manufacturer_code}")
    
    try:
        manufacturer = Manufacturer(manufacturer_code)
    except ValueError:
        raise ValueError(f"Unsupported manufacturer: {manufacturer_code}")
    
    url_pattern = MANUFACTURER_URL_PATTERNS.get(manufacturer)
    if not url_pattern:
        raise ValueError(f"No URL pattern defined for manufacturer: {manufacturer_code}")
    
    part_number_clean = part_number.lower().strip()
    url = url_pattern.format(ic_id=part_number_clean)
    
    return url


class DatasheetProvider:
    """
    Base provider for downloading datasheets from manufacturer websites.
    Uses unified storage for consistent file management.
    """
    
    def __init__(self, datasheet_root: Optional[Path] = None, manufacturer_code: str = ""):
        manufacturer_code = manufacturer_code.upper().strip()
        
        if not is_valid_manufacturer(manufacturer_code):
            raise ValueError(f"Unsupported manufacturer: {manufacturer_code}")
        
        self.datasheet_root = get_storage_folder()  # Always use unified storage
        self.manufacturer_code = manufacturer_code
        self.manufacturer_name = get_manufacturer_name(manufacturer_code)
    
    def construct_url(self, part_number: str) -> str:
        """Construct the URL for downloading the datasheet."""
        return construct_datasheet_url(self.manufacturer_code, part_number)
    
    def get_local_path(self, part_number: str, hash_value: Optional[str] = None) -> Path:
        """
        Get the local path where the datasheet will be stored.
        Uses unified storage location.
        """
        if hash_value is None:
            hash_value = generate_hash(part_number, self.manufacturer_code)
        
        return self.datasheet_root / f"{hash_value}.pdf"
    
    def get_filename(self, part_number: str) -> str:
        """
        Get the filename for the datasheet (what should be stored in DB).
        """
        return get_datasheet_filename(part_number, self.manufacturer_code)
    
    async def download(self, part_number: str) -> Tuple[Path, int, str, str]:
        """
        Download the datasheet for a part number.
        
        Returns:
            Tuple of (local_path, file_size, datasheet_url, hash_value)
        """
        url = self.construct_url(part_number)
        hash_value = generate_hash(part_number, self.manufacturer_code)
        
        # Use unified storage download
        filename, file_size = await download_pdf_async(
            url=url,
            part_number=part_number,
            manufacturer_code=self.manufacturer_code,
            timeout=settings.SCRAPE_TIMEOUT_SECONDS
        )
        
        local_path = self.datasheet_root / filename

        return local_path, file_size, url, hash_value
