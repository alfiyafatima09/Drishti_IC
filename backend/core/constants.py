"""
Application constants and enums.
Central source of truth for all constant values used across the application.
"""
from enum import Enum
from typing import Dict, List, Optional


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
    NXP = "NXP"
    ANALOG_DEVICES = "ANALOG_DEVICES"
    # ONSEMI = "ONSEMI"
    INFINEON = "INFINEON"

    # MICROCHIP = "MICROCHIP"


# Manufacturer display names (for UI and API responses)
MANUFACTURER_NAMES: Dict[str, str] = {
    Manufacturer.STM: "STMicroelectronics",
    Manufacturer.TI: "Texas Instruments",
    Manufacturer.NXP: "NXP Semiconductors",
    Manufacturer.ANALOG_DEVICES: "Analog Devices",
    # Manufacturer.ONSEMI: "onsemi",
    Manufacturer.INFINEON: "Infineon Technologies",
    # Manufacturer.MICROCHIP: "Microchip Technology",
}

# Manufacturer datasheet URL patterns
MANUFACTURER_URL_PATTERNS: Dict[str, str] = {
    Manufacturer.STM: "https://www.st.com/resource/en/datasheet/{ic_id}.pdf",
    Manufacturer.TI: "https://www.ti.com/lit/ds/symlink/{ic_id}.pdf",
    Manufacturer.NXP: "https://www.nxp.com/docs/en/data-sheet/{ic_id}.pdf",
    Manufacturer.ANALOG_DEVICES: "https://www.analog.com/media/en/technical-documentation/{ic_id}.pdf",
    # Manufacturer.ONSEMI: "https://www.onsemi.com/pdf/datasheet/{ic_id}.pdf",
    Manufacturer.INFINEON: "https://www.infineon.com/dgdl/{ic_id}.pdf",
    # Manufacturer.MICROCHIP: "https://ww1.microchip.com/downloads/en/DeviceDoc/{ic_id}.pdf",
}

# Example ICs for each manufacturer (for documentation)
MANUFACTURER_EXAMPLE_ICS: Dict[str, List[str]] = {
    Manufacturer.STM: ["stm32l031k6", "stm32f407vg", "stm32h743zi", "stm8s003f3"],
    Manufacturer.TI: ["lm555", "lm358", "tps54620", "lm7805", "ne555"],
    Manufacturer.NXP: ["MCXW23"],
    Manufacturer.INFINEON: ["XMC1100-T016F0008", "XMC1100-Q024F0016", "XMC1100-T038F0064"],
}


def get_supported_manufacturers() -> List[str]:
    """Get list of supported manufacturer codes."""
    return [m.value for m in Manufacturer]


def get_manufacturer_name(code: str) -> str:
    """Get full manufacturer name from code. Returns original code if not found."""
    if not code:
        return ""
    try:
        manufacturer = Manufacturer(code.upper())
        return MANUFACTURER_NAMES.get(manufacturer, code)
    except ValueError:
        # Return the original code if not a known manufacturer
        return code


def get_manufacturer_url_pattern(code: str) -> str:
    """Get URL pattern for manufacturer's datasheet downloads. Returns empty string if not found."""
    if not code:
        return ""
    try:
        manufacturer = Manufacturer(code.upper())
        return MANUFACTURER_URL_PATTERNS.get(manufacturer, "")
    except ValueError:
        # Return empty string if not a known manufacturer
        return ""


def get_manufacturer_details() -> Dict[str, Dict]:
    """Get detailed information about all supported manufacturers."""
    return {
        m.value: {
            "name": MANUFACTURER_NAMES.get(m, m.value),
            "url_pattern": MANUFACTURER_URL_PATTERNS.get(m, ""),
            "example_ics": MANUFACTURER_EXAMPLE_ICS.get(m, []),
        }
        for m in Manufacturer
    }


def is_valid_manufacturer(code: str) -> bool:
    """Check if manufacturer code is valid/supported."""
    try:
        Manufacturer(code.upper())
        return True
    except ValueError:
        return False


# Reverse mapping: manufacturer name variations -> enum code
MANUFACTURER_NAME_TO_CODE: Dict[str, str] = {
    # STMicroelectronics
    "STMICROELECTRONICS": Manufacturer.STM.value,
    "STM": Manufacturer.STM.value,
    "ST MICROELECTRONICS": Manufacturer.STM.value,
    "ST": Manufacturer.STM.value,
    # Texas Instruments
    "TEXAS INSTRUMENTS": Manufacturer.TI.value,
    "TI": Manufacturer.TI.value,
    # NXP
    "NXP SEMICONDUCTORS": Manufacturer.NXP.value,
    "NXP": Manufacturer.NXP.value,
    # Analog Devices
    "ANALOG DEVICES": Manufacturer.ANALOG_DEVICES.value,
    "ANALOG_DEVICES": Manufacturer.ANALOG_DEVICES.value,
    "ADI": Manufacturer.ANALOG_DEVICES.value,
    # # onsemi
    # "ONSEMI": Manufacturer.ONSEMI.value,
    # "ON SEMICONDUCTOR": Manufacturer.ONSEMI.value,
    # "ON SEMI": Manufacturer.ONSEMI.value,
    # Infineon
    "INFINEON": Manufacturer.INFINEON.value,
    "INFINEON TECHNOLOGIES": Manufacturer.INFINEON.value,
    "INFINEON TECHNOLOGIES AG": Manufacturer.INFINEON.value,
}


def get_manufacturer_code_from_name(name: str) -> Optional[str]:
    """
    Convert a manufacturer name to its enum code.
    Handles various name formats like 'Infineon Technologies' -> 'INFINEON'.

    Args:
        name: Manufacturer name (case insensitive)

    Returns:
        Manufacturer code string, or None if not found
    """
    if not name:
        return None

    normalized = name.upper().strip()

    # Direct match in name mapping
    if normalized in MANUFACTURER_NAME_TO_CODE:
        return MANUFACTURER_NAME_TO_CODE[normalized]

    # Check if it's already a valid code
    if is_valid_manufacturer(normalized):
        return normalized

    # Partial match - check if any key is contained in the name
    for key, code in MANUFACTURER_NAME_TO_CODE.items():
        if key in normalized or normalized in key:
            return code

    return None


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
    SCRAPED_INFINEON = "SCRAPED_INFINEON"
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


# ============================================================
# OCR & VISION ANALYSIS CONSTANTS
# ============================================================

# Manufacturer keywords for OCR text detection
MANUFACTURER_KEYWORDS = [
    'TEXAS', 'TI', 'STM', 'INTEL', 'MICROCHIP', 'ANALOG', 'MAXIM', 'NXP',
    'INFINEON', 'ATMEL', 'FREESCALE', 'ON SEMI', 'ONSEMI', 'FAIRCHILD',
    'NATIONAL', 'LINEAR', 'VISHAY', 'ROHM', 'TOSHIBA', 'RENESAS'
]

