"""
Base provider class for datasheet providers.
"""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Tuple, Optional

from core.constants import get_manufacturer_name
from ..downloader import generate_hash, get_local_path, download_pdf
from ..exceptions import DatasheetDownloadException

import logging

logger = logging.getLogger(__name__)


class DatasheetProvider(ABC):
    """Abstract base class for datasheet providers."""
    
    def __init__(self, datasheet_root: Path, manufacturer_code: str):
        """
        Initialize the provider with storage path and manufacturer code.
        
        Args:
            datasheet_root: Root directory for storing datasheets
            manufacturer_code: Manufacturer enum code (e.g., 'STM', 'TI')
        """
        self.datasheet_root = datasheet_root
        self.datasheet_root.mkdir(parents=True, exist_ok=True)
        self.manufacturer_code = manufacturer_code.upper()
        self.manufacturer_name = get_manufacturer_name(manufacturer_code)
    
    @abstractmethod
    def construct_url(self, part_number: str) -> str:
        """
        Construct the download URL for the IC datasheet.
        
        Args:
            part_number: IC part number (e.g., 'lm555', 'stm32l031k6')
            
        Returns:
            Full URL to the datasheet PDF
        """
        pass
    
    def get_local_path(self, part_number: str, hash_value: Optional[str] = None) -> Path:
        """
        Get the local file path for storing the datasheet.
        Uses hash-based filename: datasheets/{manufacturer}/{hash}.pdf
        
        Args:
            part_number: IC part number (used to generate hash if not provided)
            hash_value: Optional pre-generated hash (if None, generates from part_number)
            
        Returns:
            Path object for the local file
        """
        if hash_value is None:
            hash_value = generate_hash(part_number, self.manufacturer_code)
        
        return get_local_path(self.datasheet_root, self.manufacturer_code, hash_value)
    
    async def download(self, part_number: str) -> Tuple[Path, int, str, str]:
        """
        Download datasheet and save locally using hash-based filename.
        
        Args:
            part_number: IC part number
            
        Returns:
            Tuple of (file_path, file_size_bytes, datasheet_url, hash_value)
            
        Raises:
            DatasheetDownloadException: If download fails
        """
        url = self.construct_url(part_number)
        
        # Generate hash for filename
        hash_value = generate_hash(part_number, self.manufacturer_code)
        local_path = self.get_local_path(part_number, hash_value)
        
        # Download the PDF
        file_size, datasheet_url = await download_pdf(
            url=url,
            local_path=local_path,
            part_number=part_number,
            manufacturer_name=self.manufacturer_name
        )
        
        return local_path, file_size, datasheet_url, hash_value

