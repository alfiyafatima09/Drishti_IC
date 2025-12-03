"""
PDF data extractors for different manufacturers.
Each manufacturer's PDF has different structure, so separate extractors are needed.
"""
from .base import DatasheetExtractor
from .stm_extractor import STMExtractor
from .ti_extractor import TIExtractor

# Registry of supported manufacturers -> extractor classes
EXTRACTORS = {
    "STM": STMExtractor,
    "TI": TIExtractor,
}

__all__ = [
    "DatasheetExtractor",
    "STMExtractor",
    "TIExtractor",
    "EXTRACTORS",
]

