"""
Unified datasheet storage module.

All PDF downloads should use this module to ensure consistent storage.
PDFs are stored in: settings.DATASHEET_FOLDER/{hash}.pdf
Database stores: {hash}.pdf (just the filename)
"""
import hashlib
import logging
import time
from pathlib import Path
from typing import Optional, Tuple

import httpx
import requests

from core.config import settings, PROJECT_ROOT

logger = logging.getLogger(__name__)


def generate_hash(part_number: str, manufacturer_code: str) -> str:
    """
    Generate a unique hash for the datasheet filename.
    Uses part_number + manufacturer_code to create a unique identifier.
    
    Args:
        part_number: IC part number (e.g., "LM555")
        manufacturer_code: Manufacturer code (e.g., "TI", "STM")
        
    Returns:
        Hash string (first 16 chars of SHA256 hex digest)
    """
    unique_string = f"{part_number.lower().strip()}_{manufacturer_code.upper().strip()}"
    hash_obj = hashlib.sha256(unique_string.encode('utf-8'))
    return hash_obj.hexdigest()[:16]


def get_storage_folder() -> Path:
    """
    Get the datasheet storage folder (absolute path).
    Creates it if it doesn't exist.
    
    Returns:
        Absolute Path to the datasheet folder
    """
    folder = settings.DATASHEET_FOLDER.resolve()
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def get_datasheet_filename(part_number: str, manufacturer_code: str) -> str:
    """
    Get the filename for a datasheet (without folder path).
    This is what should be stored in the database.
    
    Args:
        part_number: IC part number
        manufacturer_code: Manufacturer code
        
    Returns:
        Filename like "{hash}.pdf"
    """
    hash_value = generate_hash(part_number, manufacturer_code)
    return f"{hash_value}.pdf"


def get_datasheet_path(filename_or_path: str) -> Path:
    """
    Resolve a datasheet path from database value to absolute path.
    
    Handles various formats stored in DB:
    - "{hash}.pdf" -> settings.DATASHEET_FOLDER/{hash}.pdf
    - "datasheets/ti/{hash}.pdf" -> PROJECT_ROOT/datasheets/ti/{hash}.pdf
    - "ti/{hash}.pdf" -> settings.DATASHEET_FOLDER/ti/{hash}.pdf
    - "/absolute/path/to/file.pdf" -> returns as-is
    
    Args:
        filename_or_path: The datasheet_path value from database
        
    Returns:
        Absolute Path to the datasheet file
    """
    if not filename_or_path:
        raise ValueError("Empty datasheet path")
    
    path = Path(filename_or_path)
    
    # If it's already an absolute path, return it
    if path.is_absolute():
        return path
    
    # Handle paths that start with "datasheets/" - resolve from project root
    if filename_or_path.startswith("datasheets/"):
        resolved = PROJECT_ROOT / filename_or_path
        logger.debug(f"Resolved 'datasheets/' path: {filename_or_path} -> {resolved}")
        return resolved
    
    # Handle paths with subdirectories (e.g., "ti/{hash}.pdf")
    if "/" in filename_or_path:
        resolved = get_storage_folder() / filename_or_path
        logger.debug(f"Resolved subdirectory path: {filename_or_path} -> {resolved}")
        return resolved
    
    # Simple filename - look directly in DATASHEET_FOLDER
    resolved = get_storage_folder() / filename_or_path
    logger.debug(f"Resolved simple filename: {filename_or_path} -> {resolved}")
    return resolved


def datasheet_exists(part_number: str, manufacturer_code: str) -> bool:
    """
    Check if a datasheet already exists for the given IC.
    
    Args:
        part_number: IC part number
        manufacturer_code: Manufacturer code
        
    Returns:
        True if datasheet exists, False otherwise
    """
    filename = get_datasheet_filename(part_number, manufacturer_code)
    path = get_storage_folder() / filename
    return path.exists()


def get_existing_path(part_number: str, manufacturer_code: str) -> Optional[Path]:
    """
    Get the path to an existing datasheet if it exists.
    
    Args:
        part_number: IC part number
        manufacturer_code: Manufacturer code
        
    Returns:
        Path if exists, None otherwise
    """
    filename = get_datasheet_filename(part_number, manufacturer_code)
    path = get_storage_folder() / filename
    return path if path.exists() else None


async def download_pdf_async(
    url: str,
    part_number: str,
    manufacturer_code: str,
    timeout: int = 30
) -> Tuple[str, int]:
    """
    Download a PDF asynchronously and save it to the unified storage location.
    
    Args:
        url: URL to download from
        part_number: IC part number (used for hash generation)
        manufacturer_code: Manufacturer code (used for hash generation)
        timeout: Request timeout in seconds
        
    Returns:
        Tuple of (filename, file_size_bytes)
        The filename is what should be stored in the database.
        
    Raises:
        Exception: If download fails
    """
    filename = get_datasheet_filename(part_number, manufacturer_code)
    local_path = get_storage_folder() / filename
    
    logger.info(f"Downloading PDF for {part_number} ({manufacturer_code}) from {url}")
    logger.debug(f"Saving to: {local_path}")
    
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        response = await client.get(url)
        
        if response.status_code == 404:
            raise Exception(f"Datasheet not found (HTTP 404) for {part_number}")
        
        if response.status_code != 200:
            raise Exception(f"Failed to download datasheet. HTTP {response.status_code}")
        
        content_type = response.headers.get("content-type", "")
        if "pdf" not in content_type.lower() and "octet-stream" not in content_type.lower():
            logger.warning(f"Unexpected content-type: {content_type}, proceeding anyway")
        
        with local_path.open("wb") as f:
            f.write(response.content)
        
        file_size = len(response.content)
        logger.info(f"Downloaded {file_size} bytes to {local_path}")
        
        return filename, file_size


def download_pdf_sync(
    url: str,
    part_number: str,
    manufacturer_code: str,
    timeout: int = 60,
    max_retries: int = 3
) -> Tuple[str, int]:
    """
    Download a PDF synchronously and save it to the unified storage location.
    Includes retry logic for robustness.
    
    Args:
        url: URL to download from
        part_number: IC part number (used for hash generation)
        manufacturer_code: Manufacturer code (used for hash generation)
        timeout: Request timeout in seconds
        max_retries: Maximum number of retry attempts
        
    Returns:
        Tuple of (filename, file_size_bytes)
        The filename is what should be stored in the database.
        
    Raises:
        Exception: If download fails after all retries
    """
    filename = get_datasheet_filename(part_number, manufacturer_code)
    local_path = get_storage_folder() / filename
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/pdf,*/*'
    }
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Downloading PDF for {part_number} from {url} (attempt {attempt + 1}/{max_retries})")
            
            with requests.get(url, stream=True, timeout=timeout, headers=headers) as r:
                if r.status_code == 404:
                    raise Exception(f"Datasheet not found (HTTP 404) for {part_number}")
                
                if r.status_code != 200:
                    raise Exception(f"Failed to download PDF: HTTP {r.status_code}")
                
                with local_path.open("wb") as f:
                    file_size = 0
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            file_size += len(chunk)
                
                logger.info(f"Downloaded {file_size} bytes to {local_path}")
                return filename, file_size
                
        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                logger.warning(f"Download timeout, retrying... ({attempt + 1}/{max_retries})")
                time.sleep(2)
                continue
            raise Exception(f"Download timeout after {max_retries} attempts")
        except Exception as e:
            if attempt < max_retries - 1 and "timeout" not in str(e).lower():
                logger.warning(f"Download error, retrying: {e}")
                time.sleep(1)
                continue
            raise
    
    raise Exception("Failed to download PDF after all retries")


# Manufacturer name normalization for hash generation
MANUFACTURER_NAME_MAP = {
    "stmicroelectronics": "STM",
    "stmicro": "STM",
    "st.com": "STM",
    "texas instruments": "TI",
    "ti.com": "TI",
    "onsemi": "ONSEMI",
    "on semiconductor": "ONSEMI",
    "nxp": "NXP",
    "nxp semiconductors": "NXP",
    "analog devices": "ANALOG_DEVICES",
    "adi": "ANALOG_DEVICES",
    "infineon": "INFINEON",
    "microchip": "MICROCHIP",
    "maxim": "MAXIM",
    "maxim integrated": "MAXIM",
    "renesas": "RENESAS",
    "rohm": "ROHM",
}


def normalize_manufacturer(manufacturer: str) -> str:
    """
    Normalize a manufacturer name to a standard code.
    
    Args:
        manufacturer: Manufacturer name (e.g., "Texas Instruments", "STMicroelectronics")
        
    Returns:
        Normalized manufacturer code (e.g., "TI", "STM")
    """
    if not manufacturer:
        return "UNKNOWN"
    
    mfr_lower = manufacturer.lower().strip()
    
    # Check direct mapping
    if mfr_lower in MANUFACTURER_NAME_MAP:
        return MANUFACTURER_NAME_MAP[mfr_lower]
    
    # Check partial matches
    for key, code in MANUFACTURER_NAME_MAP.items():
        if key in mfr_lower:
            return code
    
    # Fallback: use first word, sanitized
    return manufacturer.split()[0].upper().replace(",", "").replace(".", "")[:20]

