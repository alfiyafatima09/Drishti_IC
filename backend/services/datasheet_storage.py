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
from urllib.parse import urlparse, parse_qs, unquote

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
    Includes automatic URL resolution for TI webview and redirects.
    
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
    # Resolve URL (handle TI webview and redirects) - use sync version since it's just URL parsing
    resolved_url = resolve_url(url)
    
    filename = get_datasheet_filename(part_number, manufacturer_code)
    local_path = get_storage_folder() / filename
    
    logger.info(f"Downloading PDF for {part_number} ({manufacturer_code}) from {resolved_url}")
    logger.debug(f"Saving to: {local_path}")
    
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        response = await client.get(resolved_url)
        
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
    Includes retry logic for robustness and automatic URL resolution.
    
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
    # Resolve URL (handle TI webview and redirects)
    resolved_url = resolve_url(url)
    
    filename = get_datasheet_filename(part_number, manufacturer_code)
    local_path = get_storage_folder() / filename
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/pdf,*/*'
    }
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Downloading PDF for {part_number} from {resolved_url} (attempt {attempt + 1}/{max_retries})")
            
            with requests.get(resolved_url, stream=True, timeout=timeout, headers=headers) as r:
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


def resolve_ti_webview_url(url: str) -> str:
    """
    Resolve TI webview redirect URLs to actual PDF URLs.

    TI often provides URLs like:
    https://www.ti.com/general/docs/suppproductinfo.tsp?distId=10&gotoUrl=http%253A%252F%252Fwww.ti.com%252Flit%252Fgpn%252Flm224

    The actual PDF URL is in the gotoUrl parameter (double URL-encoded).
    
    Args:
        url: Original URL that might be a TI webview redirect
        
    Returns:
        Resolved URL (or original if not a TI webview URL)
    """
    if "suppproductinfo.tsp" not in url and "ti.com/general/docs" not in url:
        return url

    try:
        parsed = urlparse(url)
        query_params = parse_qs(parsed.query)

        if "gotoUrl" in query_params:
            # The gotoUrl is double URL-encoded
            goto_url = query_params["gotoUrl"][0]
            # Decode twice
            actual_url = unquote(unquote(goto_url))
            logger.info(f"Resolved TI webview URL: {url} -> {actual_url}")
            return actual_url
    except Exception as e:
        logger.warning(f"Failed to parse TI webview URL: {e}")

    return url


def extract_pdf_from_preview_page(url: str, timeout: int = 30) -> Optional[str]:
    """
    Some URLs (like OnSemi Widen CDN) return HTML preview pages with embedded PDF URLs.
    This function fetches the page and extracts the actual PDF URL from JavaScript.
    
    Args:
        url: URL that might be an HTML preview page
        timeout: Request timeout in seconds
        
    Returns:
        Extracted PDF URL if found, None otherwise
    """
    try:
        import re
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        }
        
        resp = requests.get(url, headers=headers, timeout=timeout)
        
        if resp.status_code != 200:
            return None
            
        content_type = resp.headers.get('content-type', '').lower()
        
        # If it's already a PDF, return the URL as-is
        if 'application/pdf' in content_type:
            return url
            
        # If it's HTML, try to extract PDF URL from JavaScript
        if 'text/html' in content_type:
            html_content = resp.text
            
            # Pattern 1: window.viewerPdfUrl = 'URL'
            match = re.search(r'window\.viewerPdfUrl\s*=\s*[\'"]([^\'\"]+)[\'"]', html_content)
            if match:
                pdf_url = match.group(1)
                logger.info(f"Extracted PDF URL from preview page: {pdf_url}")
                return pdf_url
            
            # Pattern 2: data-pdf-url="URL"
            match = re.search(r'data-pdf-url=[\'"]([^\'\"]+)[\'"]', html_content)
            if match:
                pdf_url = match.group(1)
                logger.info(f"Extracted PDF URL from data attribute: {pdf_url}")
                return pdf_url
            
            # Pattern 3: Look for .pdf URLs in the HTML
            pdf_urls = re.findall(r'https?://[^\s\'"<>]+\.pdf[^\s\'"<>]*', html_content)
            if pdf_urls:
                pdf_url = pdf_urls[0]
                logger.info(f"Found PDF URL in HTML: {pdf_url}")
                return pdf_url
                
        return None
        
    except Exception as e:
        logger.warning(f"Failed to extract PDF from preview page {url}: {e}")
        return None


def follow_redirects(url: str, timeout: int = 30) -> str:
    """
    Follow HTTP redirects to get the final PDF URL.
    TI's /lit/gpn/ URLs and other manufacturer URLs often redirect to the actual PDF.
    
    Args:
        url: Original URL
        timeout: Request timeout in seconds
        
    Returns:
        Final URL after following all redirects
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/pdf,*/*'
        }
        # Use HEAD request to follow redirects without downloading
        resp = requests.head(url, allow_redirects=True, timeout=timeout, headers=headers)
        
        if resp.url != url:
            logger.info(f"Followed redirect: {url} -> {resp.url}")
            return resp.url
        
        return url
        
    except Exception as e:
        logger.warning(f"Failed to follow redirects for {url}: {e}")
        return url


def resolve_url(url: str) -> str:
    """
    Resolve a datasheet URL by handling TI webview URLs, preview pages, and following redirects.
    This should be called before downloading to ensure we have the actual PDF URL.
    
    Args:
        url: Original datasheet URL
        
    Returns:
        Resolved URL ready for download
    """
    # First, resolve TI webview URLs (double URL-encoded)
    url = resolve_ti_webview_url(url)
    
    # Then, try to extract PDF URL from preview pages (OnSemi Widen CDN, etc.)
    extracted_url = extract_pdf_from_preview_page(url)
    if extracted_url:
        url = extracted_url
    
    # Finally, follow any HTTP redirects
    url = follow_redirects(url)
    
    return url


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
    "atmel": "ATMEL",
    "maxim": "MAXIM",
    "maxim integrated": "MAXIM",
    "renesas": "RENESAS",
    "rohm": "ROHM",
    "raspberry pi": "RASPBERRY_PI",
    "raspberry pi ltd": "RASPBERRY_PI",
    "raspberrypi": "RASPBERRY_PI",
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

