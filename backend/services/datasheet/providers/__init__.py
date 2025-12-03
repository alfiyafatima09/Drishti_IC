

from .provider import DatasheetProvider, construct_datasheet_url
from core.constants import get_supported_manufacturers

def create_provider(datasheet_root, manufacturer_code: str) -> DatasheetProvider:
    return DatasheetProvider(datasheet_root, manufacturer_code)

PROVIDERS = {
    mfr: DatasheetProvider
    for mfr in get_supported_manufacturers()
}

__all__ = [
    "DatasheetProvider",
    "construct_datasheet_url",
    "create_provider",
    "PROVIDERS",
]

