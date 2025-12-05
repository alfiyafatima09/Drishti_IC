"""
PDF data extractors for different manufacturers.
Each manufacturer's PDF has different structure, so separate extractors are needed.
"""
from .base import DatasheetExtractor
from .stm_extractor import STMExtractor
from .ti_extractor import TIExtractor
from .onsemi_extractor import OnSemiExtractor
from .nxp_extractor import NXPExtractor

# Registry of supported manufacturers -> extractor classes
EXTRACTORS = {
    "STM": STMExtractor,
    "TI": TIExtractor,
    "ONSEMI": OnSemiExtractor,
    "NXP": NXPExtractor,
}

__all__ = [
    "DatasheetExtractor",
    "STMExtractor",
    "TIExtractor",
    "OnSemiExtractor",
    "NXPExtractor",
    "EXTRACTORS",
]

