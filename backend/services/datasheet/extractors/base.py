"""
Base extractor class for PDF data extraction.
Each manufacturer's PDF has different structure.
"""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional

from ..exceptions import DatasheetExtractionException

import logging

logger = logging.getLogger(__name__)


class DatasheetExtractor(ABC):
    """Abstract base class for extracting data from PDF datasheets."""
    
    def __init__(self, manufacturer_code: str):
        """
        Initialize the extractor.
        
        Args:
            manufacturer_code: Manufacturer enum code (e.g., 'STM', 'TI')
        """
        self.manufacturer_code = manufacturer_code.upper()
    
    @abstractmethod
    def extract(self, pdf_path: Path) -> List[Dict]:
        """
        Extract IC specification data from PDF datasheet.
        A single PDF can contain multiple IC variants (e.g., LM317DCY, LM317KCS).
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            List of dictionaries, each containing extracted data for one IC variant:
            [
                {
                    "part_number": str,  # e.g., "LM317DCY"
                    "manufacturer": str,
                    "pin_count": int,
                    "package_type": str,  # e.g., "SOT-223", "TO-220"
                    "description": str,
                    "voltage_min": float,
                    "voltage_max": float,
                    "operating_temp_min": float,
                    "operating_temp_max": float,
                    "electrical_specs": dict,
                },
                ...
            ]
            
        Raises:
            DatasheetExtractionException: If extraction fails
        """
        pass
    
    def extract_basic_info(self, pdf_path: Path) -> Dict:
        """
        Extract basic information from PDF (placeholder for now).
        Override in subclasses for manufacturer-specific extraction.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Dictionary with basic extracted data
        """
        # TODO: Implement PDF parsing
        # For now, return minimal data
        return {
            "pin_count": 0,  # Will be extracted from PDF
            "package_type": None,
            "description": None,
            "voltage_min": None,
            "voltage_max": None,
            "operating_temp_min": None,
            "operating_temp_max": None,
            "electrical_specs": {},
        }

