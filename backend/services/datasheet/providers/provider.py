from pathlib import Path
from typing import Tuple, Optional

from core.constants import (
    Manufacturer,
    get_manufacturer_name,
    MANUFACTURER_URL_PATTERNS,
    is_valid_manufacturer,
)
from ..downloader import generate_hash, download_pdf
from core.config import settings

def construct_datasheet_url(manufacturer_code: str, part_number: str) -> str:
    manufacturer_code = manufacturer_code.upper().strip()
    
    if not is_valid_manufacturer(manufacturer_code):
        raise ValueError(f"Unsupported manufacturer: {manufacturer_code}")
    
    try: manufacturer = Manufacturer(manufacturer_code)
    except ValueError: raise ValueError(f"Unsupported manufacturer: {manufacturer_code}")
    
    url_pattern = MANUFACTURER_URL_PATTERNS.get(manufacturer)
    if not url_pattern: raise ValueError(f"No URL pattern defined for manufacturer: {manufacturer_code}")
    
    part_number_clean = part_number.lower().strip()
    url = url_pattern.format(ic_id=part_number_clean)
    
    return url


class DatasheetProvider:
    def __init__(self, datasheet_root: Optional[Path] = None, manufacturer_code: str = ""):
        manufacturer_code = manufacturer_code.upper().strip()
        
        if not is_valid_manufacturer(manufacturer_code):
            raise ValueError(f"Unsupported manufacturer: {manufacturer_code}")
        
        self.datasheet_root = datasheet_root or settings.DATASHEET_FOLDER
        self.manufacturer_code = manufacturer_code
        self.manufacturer_name = get_manufacturer_name(manufacturer_code)
    
    def construct_url(self, part_number: str) -> str:
        return construct_datasheet_url(self.manufacturer_code, part_number)
    
    def get_local_path(self, part_number: str, hash_value: Optional[str] = None) -> Path:
        if hash_value is None:
            hash_value = generate_hash(part_number, self.manufacturer_code)
        
        return settings.DATASHEET_FOLDER / f"{hash_value}.pdf"
    
    async def download(self, part_number: str) -> Tuple[Path, int, str, str]:
        url = self.construct_url(part_number)
        
        hash_value = generate_hash(part_number, self.manufacturer_code)
        local_path = self.get_local_path(part_number, hash_value)
        
        file_size, datasheet_url = await download_pdf(
            url=url,
            local_path=local_path,
            part_number=part_number,
            manufacturer_name=self.manufacturer_name
        )
        
        return local_path, file_size, datasheet_url, hash_value

