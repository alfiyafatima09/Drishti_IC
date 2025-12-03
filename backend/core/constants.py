"""
Application constants and enums.
Central source of truth for all constant values used across the application.
"""
from enum import Enum
from typing import Dict, List


# ============================================================
# MANUFACTURER CONSTANTS
# ============================================================

class Manufacturer(str, Enum):
    """
    Supported IC manufacturers.
    Add new manufacturers here when adding provider support.
    """
    STM = "STM"
    TI = "TI"
    # Add more manufacturers as support is implemented:
    # MICROCHIP = "MICROCHIP"
    # NXP = "NXP"
    # ANALOG_DEVICES = "ANALOG_DEVICES"
    # INFINEON = "INFINEON"
    # ONSEMI = "ONSEMI"


# Manufacturer display names (for UI and API responses)
MANUFACTURER_NAMES: Dict[str, str] = {
    Manufacturer.STM: "STMicroelectronics",
    Manufacturer.TI: "Texas Instruments",
    # Add more as needed:
    # Manufacturer.MICROCHIP: "Microchip Technology",
    # Manufacturer.NXP: "NXP Semiconductors",
    # Manufacturer.ANALOG_DEVICES: "Analog Devices",
    # Manufacturer.INFINEON: "Infineon Technologies",
    # Manufacturer.ONSEMI: "onsemi",
}

# Manufacturer datasheet URL patterns
MANUFACTURER_URL_PATTERNS: Dict[str, str] = {
    Manufacturer.STM: "https://www.st.com/resource/en/datasheet/{ic_id}.pdf",
    Manufacturer.TI: "https://www.ti.com/lit/ds/symlink/{ic_id}.pdf",
    # Add more as needed:
    # Manufacturer.MICROCHIP: "https://ww1.microchip.com/downloads/en/DeviceDoc/{ic_id}.pdf",
}

# Example ICs for each manufacturer (for documentation)
MANUFACTURER_EXAMPLE_ICS: Dict[str, List[str]] = {
    Manufacturer.STM: ["stm32l031k6", "stm32f407vg", "stm32h743zi", "stm8s003f3"],
    Manufacturer.TI: ["lm555", "lm358", "tps54620", "lm7805", "ne555"],
    # Add more as needed:
    # Manufacturer.MICROCHIP: ["atmega328p", "pic16f877a", "attiny85"],
}


def get_supported_manufacturers() -> List[str]:
    """Get list of supported manufacturer codes."""
    return [m.value for m in Manufacturer]


def get_manufacturer_name(code: str) -> str:
    """
    Get full manufacturer name from code.
    
    Args:
        code: Manufacturer code (e.g., "TI")
        
    Returns:
        Full name (e.g., "Texas Instruments")
        
    Raises:
        ValueError: If manufacturer code is not supported
    """
    try:
        manufacturer = Manufacturer(code.upper())
        return MANUFACTURER_NAMES.get(manufacturer, code)
    except ValueError:
        raise ValueError(f"Unsupported manufacturer: {code}")


def get_manufacturer_url_pattern(code: str) -> str:
    """
    Get URL pattern for manufacturer's datasheet downloads.
    
    Args:
        code: Manufacturer code (e.g., "TI")
        
    Returns:
        URL pattern with {ic_id} placeholder
        
    Raises:
        ValueError: If manufacturer code is not supported
    """
    try:
        manufacturer = Manufacturer(code.upper())
        return MANUFACTURER_URL_PATTERNS.get(manufacturer, "")
    except ValueError:
        raise ValueError(f"Unsupported manufacturer: {code}")


def get_manufacturer_details() -> Dict[str, Dict]:
    """
    Get detailed information about all supported manufacturers.
    Used by the /api/v1/datasheets/manufacturers endpoint.
    
    Returns:
        Dictionary with manufacturer details
    """
    return {
        m.value: {
            "name": MANUFACTURER_NAMES.get(m, m.value),
            "url_pattern": MANUFACTURER_URL_PATTERNS.get(m, ""),
            "example_ics": MANUFACTURER_EXAMPLE_ICS.get(m, []),
        }
        for m in Manufacturer
    }


def is_valid_manufacturer(code: str) -> bool:
    """
    Check if manufacturer code is valid/supported.
    
    Args:
        code: Manufacturer code to validate
        
    Returns:
        True if valid, False otherwise
    """
    try:
        Manufacturer(code.upper())
        return True
    except ValueError:
        return False


# ============================================================
# SCAN STATUS CONSTANTS
# ============================================================

class ScanStatus(str, Enum):
    """Possible scan result statuses."""
    PASS = "PASS"
    FAIL = "FAIL"
    PARTIAL = "PARTIAL"
    UNKNOWN = "UNKNOWN"
    COUNTERFEIT = "COUNTERFEIT"


class ActionRequired(str, Enum):
    """Actions that may be required after a scan."""
    NONE = "NONE"
    SCAN_BOTTOM = "SCAN_BOTTOM"


# ============================================================
# QUEUE STATUS CONSTANTS
# ============================================================

class QueueStatus(str, Enum):
    """Status values for datasheet queue items."""
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    FAILED = "FAILED"


# ============================================================
# SYNC JOB STATUS CONSTANTS
# ============================================================

class SyncJobStatus(str, Enum):
    """Status values for sync jobs."""
    IDLE = "IDLE"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    ERROR = "ERROR"
    CANCELLED = "CANCELLED"


# ============================================================
# FAKE REGISTRY SOURCE CONSTANTS
# ============================================================

class FakeSource(str, Enum):
    """Source of fake registry entries."""
    SYNC_NOT_FOUND = "SYNC_NOT_FOUND"
    MANUAL_REPORT = "MANUAL_REPORT"


# ============================================================
# IC SPECIFICATION SOURCE CONSTANTS
# ============================================================

class ICSource(str, Enum):
    """Source of IC specification data."""
    MANUAL = "MANUAL"
    SCRAPED_STM = "SCRAPED_STM"
    SCRAPED_TI = "SCRAPED_TI"
    SCRAPED_MOUSER = "SCRAPED_MOUSER"
    SCRAPED_DIGIKEY = "SCRAPED_DIGIKEY"
    SCRAPED_ALLDATASHEET = "SCRAPED_ALLDATASHEET"


# ============================================================
# DATASHEET DOWNLOAD STATUS
# ============================================================

class DatasheetDownloadStatus(str, Enum):
    """Status of individual datasheet download attempt."""
    SUCCESS = "SUCCESS"
    NOT_FOUND = "NOT_FOUND"
    TIMEOUT = "TIMEOUT"
    ERROR = "ERROR"


# ============================================================
# SETTING VALUE TYPES
# ============================================================

class SettingValueType(str, Enum):
    """Types for settings values."""
    STRING = "STRING"
    INTEGER = "INTEGER"
    FLOAT = "FLOAT"
    BOOLEAN = "BOOLEAN"
    JSON = "JSON"

