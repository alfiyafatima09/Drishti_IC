"""
Datasheet provider implementations.
Each manufacturer has its own provider for URL construction.
"""
from .base import DatasheetProvider
from .stm import STMProvider
from .ti import TIProvider

# Registry of supported manufacturers -> provider classes
PROVIDERS = {
    "STM": STMProvider,
    "TI": TIProvider,
}

__all__ = [
    "DatasheetProvider",
    "STMProvider",
    "TIProvider",
    "PROVIDERS",
]

