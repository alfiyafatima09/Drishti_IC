"""
PDF parser for datasheet processing.

Uses manufacturer-specific extractors to parse PDF datasheets and extract
IC specifications like part numbers, pin counts, voltage ranges, etc.
"""
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


def parse_pdf(path: Path, manufacturer: Optional[str] = None) -> Dict[str, Any]:
    """
    Parse a PDF datasheet and extract IC specifications.
    
    Args:
        path: Path to the PDF file
        manufacturer: Manufacturer name or code (e.g., 'STM', 'STMicroelectronics', 'TI'). If None, attempts to detect.
    
    Returns:
        Dictionary containing:
        - status: "success" or "error"
        - path: Path to the PDF
        - manufacturer: Detected/provided manufacturer
        - ic_variants: List of extracted IC specifications
        - error: Error message if parsing failed
    """
    if not Path(path).exists():
        raise FileNotFoundError(f"PDF not found: {path}")

    logger.info("Parsing PDF: %s (manufacturer=%s)", path, manufacturer or "auto-detect")
    
    try:
        # Import extractors here to avoid circular imports
        from services.datasheet.extractors import EXTRACTORS
        
        # Normalize manufacturer name to code
        if manufacturer:
            manufacturer = _normalize_manufacturer(manufacturer)
        
        # Auto-detect manufacturer from filename if not provided or normalization failed
        if not manufacturer:
            manufacturer = _detect_manufacturer(path)
        
        if not manufacturer or manufacturer.upper() not in EXTRACTORS:
            logger.warning(f"Unsupported or unknown manufacturer: {manufacturer}")
            return {
                "status": "error",
                "path": str(path),
                "manufacturer": manufacturer,
                "ic_variants": [],
                "error": f"Unsupported manufacturer: {manufacturer}"
            }
        
        # Get the appropriate extractor
        extractor_class = EXTRACTORS[manufacturer.upper()]
        extractor = extractor_class(manufacturer.upper())
        
        # Extract IC specifications
        ic_variants = extractor.extract(path)
        
        logger.info(f"Successfully extracted {len(ic_variants)} IC variant(s) from PDF")
        
        return {
            "status": "success",
            "path": str(path),
            "manufacturer": manufacturer.upper(),
            "ic_variants": ic_variants,
            "total_variants": len(ic_variants)
        }
        
    except Exception as e:
        logger.error(f"Failed to parse PDF {path}: {e}", exc_info=True)
        return {
            "status": "error",
            "path": str(path),
            "manufacturer": manufacturer,
            "ic_variants": [],
            "error": str(e)
        }


def _normalize_manufacturer(manufacturer: str) -> Optional[str]:
    """
    Normalize manufacturer name to standard code.

    Maps common manufacturer names to standard codes:
    - STMicroelectronics -> STM
    - Texas Instruments -> TI
    - onsemi -> ONSEMI
    - Infineon Technologies -> INFINEON
    - etc.

    Returns:
        Normalized manufacturer code, or None if unknown
    """
    if not manufacturer:
        return None

    # Use centralized mapping from constants
    from core.constants import get_manufacturer_code_from_name
    code = get_manufacturer_code_from_name(manufacturer)
    if code:
        return code

    # Fallback to legacy logic for backwards compatibility
    mfr_lower = manufacturer.lower()

    # Map to standard manufacturer codes
    if "stmicro" in mfr_lower or "st.com" in mfr_lower:
        return "STM"
    elif "texas" in mfr_lower or "ti.com" in mfr_lower:
        return "TI"
    elif "onsemi" in mfr_lower or "on semiconductor" in mfr_lower:
        return "ONSEMI"
    elif "nxp" in mfr_lower:
        return "NXP"
    elif "analog" in mfr_lower:
        return "ANALOG_DEVICES"
    elif "microchip" in mfr_lower or "atmel" in mfr_lower:
        return "MICROCHIP"
    elif "infineon" in mfr_lower:
        return "INFINEON"
    else:
        # Return as-is if already a code
        return manufacturer.upper()


def _detect_manufacturer(path: Path) -> Optional[str]:
    """
    Attempt to detect manufacturer from PDF filename or path.

    Common patterns:
    - STM: st.com, stmicroelectronics
    - TI: ti.com, texas instruments
    - ONSEMI: onsemi.com, on semiconductor
    - NXP: nxp.com
    - Analog Devices: analog.com, analogdevices
    - Infineon: infineon.com, infineon
    """
    path_str = str(path).lower()

    # Check for manufacturer keywords in path/filename
    # Order matters - check most specific patterns first
    if any(keyword in path_str for keyword in ['st.com', 'stmicroelectronics', 'stmicro']):
        logger.info(f"Detected STM manufacturer from path: {path}")
        return 'STM'
    elif any(keyword in path_str for keyword in ['ti.com', 'texas', 'texasinstruments']):
        logger.info(f"Detected TI manufacturer from path: {path}")
        return 'TI'
    elif any(keyword in path_str for keyword in ['onsemi.com', 'onsemi', 'on semiconductor']):
        logger.info(f"Detected ONSEMI manufacturer from path: {path}")
        return 'ONSEMI'
    elif any(keyword in path_str for keyword in ['nxp.com', 'nxp']):
        logger.info(f"Detected NXP manufacturer from path: {path}")
        return 'NXP'
    elif any(keyword in path_str for keyword in ['analog.com', 'analogdevices']):
        logger.info(f"Detected ANALOG_DEVICES manufacturer from path: {path}")
        return 'ANALOG_DEVICES'
    elif any(keyword in path_str for keyword in ['microchip.com', 'microchip', 'atmel']):
        logger.info(f"Detected MICROCHIP manufacturer from path: {path}")
        return 'MICROCHIP'
    elif any(keyword in path_str for keyword in ['infineon.com', 'infineon']):
        logger.info(f"Detected INFINEON manufacturer from path: {path}")
        return 'INFINEON'
    elif any(keyword in path_str for keyword in ['analog.com', 'analog_devices', 'analogdevices', 'adi']):
        logger.info(f"Detected ANALOG_DEVICES manufacturer from path: {path}")
        return 'ANALOG_DEVICES'

    logger.warning(f"Could not auto-detect manufacturer from path: {path}")
    return None
