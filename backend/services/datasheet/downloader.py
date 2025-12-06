"""
Datasheet downloader module.
Handles downloading PDFs from manufacturer URLs.
"""
import logging
import httpx
import hashlib
from pathlib import Path
from typing import Tuple

from core.config import settings
from .exceptions import DatasheetDownloadException

logger = logging.getLogger(__name__)


def generate_hash(part_number: str, manufacturer_code: str) -> str:
    """
    Generate a hash for the datasheet filename.
    Uses part_number + manufacturer_code to create a unique hash.
    
    Args:
        part_number: IC part number
        manufacturer_code: Manufacturer code (e.g., 'TI', 'STM')
        
    Returns:
        Hash string (first 16 chars of SHA256 hex digest)
    """
    unique_string = f"{part_number.lower().strip()}_{manufacturer_code.upper()}"
    hash_obj = hashlib.sha256(unique_string.encode('utf-8'))
    return hash_obj.hexdigest()[:16]


async def download_pdf(
    url: str,
    local_path: Path,
    part_number: str,
    manufacturer_name: str
) -> Tuple[int, str]:
    """
    Download PDF from URL and save to local path.
    
    Args:
        url: URL to download from
        local_path: Path where to save the file
        part_number: IC part number (for logging)
        manufacturer_name: Manufacturer name (for logging)
        
    Returns:
        Tuple of (file_size_bytes, datasheet_url)
        
    Raises:
        DatasheetDownloadException: If download fails
    """
    logger.info(
        f"Downloading {manufacturer_name} datasheet for {part_number} from {url}. "
        f"Path: {local_path}"
    )
    
    try:
        async with httpx.AsyncClient(
            timeout=settings.SCRAPE_TIMEOUT_SECONDS,
            follow_redirects=True
        ) as client:
            response = await client.get(url)
            
            if response.status_code == 404:
                raise DatasheetDownloadException(
                    f"Datasheet not found (HTTP 404) for {part_number} from {manufacturer_name}"
                )
            
            if response.status_code != 200:
                raise DatasheetDownloadException(
                    f"Failed to download datasheet. HTTP {response.status_code}"
                )
            
            content_type = response.headers.get("content-type", "")
            if "pdf" not in content_type.lower() and "application/octet-stream" not in content_type.lower():
                raise DatasheetDownloadException(
                    f"Downloaded file is not a PDF. Content-Type: {content_type}"
                )
            
            with local_path.open("wb") as f:
                f.write(response.content)
            
            file_size = len(response.content)
            logger.info(
                f"Successfully downloaded {manufacturer_name} datasheet for {part_number}. "
                f"Size: {file_size} bytes. Saved to: {local_path}"
            )
            
            return file_size, url
            
    except httpx.TimeoutException as e:
        logger.error(f"Timeout while downloading datasheet for {part_number}: {e}")
        raise DatasheetDownloadException(
            f"Download timeout for {part_number} from {manufacturer_name}"
        )
    except httpx.RequestError as e:
        logger.error(f"Network error while downloading datasheet for {part_number}: {e}")
        raise DatasheetDownloadException(
            f"Network error while downloading datasheet for {part_number}: {str(e)}"
        )
    except OSError as e:
        logger.error(f"File system error while saving datasheet for {part_number}: {e}")
        raise DatasheetDownloadException(
            f"Failed to save datasheet for {part_number}: {str(e)}"
        )

