"""
Digikey API integration service.

Responsibilities:
- Obtain OAuth2 token using client credentials
- Search products by keyword
- Extract the datasheet URL for the first manufacturer/first product
- Download the datasheet PDF using unified storage
"""
import logging
import time
from typing import Optional, Dict, Any

import requests

from core.config import settings
from services.datasheet_storage import (
    download_pdf_sync,
    normalize_manufacturer,
)

logger = logging.getLogger(__name__)


class DigiKeyException(Exception):
    pass


class DigiKeyService:
    def __init__(self):
        self.client_id = settings.DIGIKEY_CLIENT_ID
        self.client_secret = settings.DIGIKEY_CLIENT_SECRET
        self.token_url = settings.DIGIKEY_TOKEN_URL
        self.search_url = settings.DIGIKEY_SEARCH_URL
        self._token: Optional[str] = None
        self._token_expiry: float = 0.0

    def _get_token(self) -> str:
        now = time.time()
        if self._token and now < self._token_expiry - 30:
            return self._token

        payload = {"grant_type": "client_credentials"}
        auth = (self.client_id, self.client_secret)
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        resp = requests.post(self.token_url, data=payload, auth=auth, headers=headers, timeout=15)
        if resp.status_code != 200:
            logger.error("Failed to fetch DigiKey token: %s %s", resp.status_code, resp.text)
            raise DigiKeyException(f"Failed to fetch token: {resp.status_code}")

        data = resp.json()
        access_token = data.get("access_token") or data.get("token")
        expires_in = int(data.get("expires_in", 3600))
        if not access_token:
            logger.error("Token response missing access_token: %s", data)
            raise DigiKeyException("Token response invalid")

        self._token = access_token
        self._token_expiry = now + expires_in
        return self._token

    def search_keyword(self, keyword: str) -> Dict[str, Any]:
        """Search Digikey products using keyword search endpoint."""
        token = self._get_token()

        headers = {
            "accept": "application/json",
            "authorization": f"Bearer {token}",
            "X-DIGIKEY-Client-Id": self.client_id,
            "Content-Type": "application/json",
        }

        payload = {"Keywords": keyword}

        resp = requests.post(self.search_url, json=payload, headers=headers, timeout=20)
        if resp.status_code != 200:
            logger.error("DigiKey search failed: %s %s", resp.status_code, resp.text)
            raise DigiKeyException(f"Search failed: {resp.status_code}")

        return resp.json()

    def extract_first_datasheet_info(self, search_response: Dict[str, Any]) -> Optional[Dict[str, str]]:
        """Extract datasheet URL and manufacturer for the first product from DigiKey v4 API response."""
        products = search_response.get("Products") or search_response.get("products")
        if not products or len(products) == 0:
            logger.warning("No products found in DigiKey search response")
            return None

        first_product = products[0]
        datasheet_url = first_product.get("DatasheetUrl")
        
        if not (datasheet_url and isinstance(datasheet_url, str) and datasheet_url.strip()):
            logger.warning("No DatasheetUrl found in first product: %s", first_product.get("ManufacturerProductNumber", "unknown"))
            return None
        
        manufacturer_obj = first_product.get("Manufacturer", {})
        manufacturer_name = ""
        if isinstance(manufacturer_obj, dict):
            manufacturer_name = manufacturer_obj.get("Name", "")
        
        # Get the part number from the product
        part_number = first_product.get("ManufacturerProductNumber", "")
        
        logger.info("Found datasheet URL: %s (Manufacturer: %s, Part: %s)", 
                   datasheet_url, manufacturer_name, part_number)
        
        return {
            "url": datasheet_url,
            "manufacturer": manufacturer_name,
            "part_number": part_number,
        }
    
    def extract_first_datasheet_url(self, search_response: Dict[str, Any]) -> Optional[str]:
        """Legacy method - extract just the URL."""
        info = self.extract_first_datasheet_info(search_response)
        return info["url"] if info else None

    def download_pdf(
        self, 
        url: str, 
        part_number: str,
        manufacturer: Optional[str] = None
    ) -> str:
        """
        Download a PDF and save it using unified storage.
        URL resolution (TI webview, redirects) is handled automatically by datasheet_storage.

        Args:
            url: URL to download PDF from
            part_number: IC part number (required for consistent hashing)
            manufacturer: Manufacturer name (will be normalized)

        Returns:
            The filename stored (to be saved in database)
            
        Raises:
            DigiKeyException: If download fails
        """
        if not url or not url.startswith("http"):
            raise DigiKeyException("Invalid URL to download")

        if not part_number:
            raise DigiKeyException("Part number is required for download")

        # Normalize manufacturer code
        manufacturer_code = normalize_manufacturer(manufacturer or "UNKNOWN")
        
        try:
            filename, file_size = download_pdf_sync(
                url=url,
                part_number=part_number,
                manufacturer_code=manufacturer_code,
                timeout=60,
                max_retries=3
            )
            
            logger.info(f"DigiKey: Downloaded {file_size} bytes as {filename}")
            return filename
            
        except Exception as e:
            logger.error(f"DigiKey download error: {e}")
            raise DigiKeyException(f"Failed to download PDF: {str(e)}")


digi_service = DigiKeyService()


def search_and_download_datasheet(keyword: str) -> Dict[str, Any]:
    """
    Convenience wrapper: search by keyword and download first datasheet PDF.

    Returns dict with:
    - 'filename': The filename stored (e.g., "abc123def456.pdf")
    - 'manufacturer': The manufacturer name
    - 'manufacturer_code': Normalized manufacturer code
    - 'part_number': The part number from DigiKey
    """
    resp = digi_service.search_keyword(keyword)
    info = digi_service.extract_first_datasheet_info(resp)
    if not info:
        raise DigiKeyException("No datasheet URL found in search response")

    part_number = info.get("part_number") or keyword
    manufacturer = info.get("manufacturer", "Unknown")
    manufacturer_code = normalize_manufacturer(manufacturer)
    
    filename = digi_service.download_pdf(
        url=info["url"],
        part_number=part_number,
        manufacturer=manufacturer
    )
    
    return {
        "filename": filename,
        "manufacturer": manufacturer,
        "manufacturer_code": manufacturer_code,
        "part_number": part_number,
    }
