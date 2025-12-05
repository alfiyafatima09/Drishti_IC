"""
Digikey API integration service.

Responsibilities:
- Obtain OAuth2 token using client credentials
- Search products by keyword
- Extract the datasheet URL for the first manufacturer/first product
- Download the datasheet PDF to the datasheet folder

This is implemented as a pragmatic service: error handling is conservative and
callers should handle exceptions appropriately.
"""
import base64
import logging
import time
from pathlib import Path
from typing import Optional, Dict, Any

import requests

from core.config import settings

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

        # Request a new token via client credentials
        payload = {
            "grant_type": "client_credentials"
        }

        # Digikey documentation commonly supports basic auth with client id/secret
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
        """Search Digikey products using keyword search endpoint.

        Returns the parsed JSON response.
        """
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
        """Extract datasheet URL and manufacturer for the first product from DigiKey v4 API response.

        The v4 API returns a 'Products' array where each product has a 'DatasheetUrl' field.
        We extract the DatasheetUrl and Manufacturer from the first product in the list.
        
        Returns:
            Dict with 'url' and 'manufacturer' keys, or None if not found
        """
        # DigiKey v4 API response contains 'Products' array
        products = search_response.get("Products") or search_response.get("products")
        if not products or len(products) == 0:
            logger.warning("No products found in DigiKey search response")
            return None

        first_product = products[0]
        
        # DigiKey v4 API provides 'DatasheetUrl' directly on the product
        datasheet_url = first_product.get("DatasheetUrl")
        
        if not (datasheet_url and isinstance(datasheet_url, str) and datasheet_url.strip()):
            logger.warning("No DatasheetUrl found in first product: %s", first_product.get("ManufacturerProductNumber", "unknown"))
            return None
        
        # Extract manufacturer name
        manufacturer_obj = first_product.get("Manufacturer", {})
        manufacturer_name = ""
        if isinstance(manufacturer_obj, dict):
            manufacturer_name = manufacturer_obj.get("Name", "")
        
        logger.info("Found datasheet URL: %s (Manufacturer: %s)", datasheet_url, manufacturer_name)
        
        return {
            "url": datasheet_url,
            "manufacturer": manufacturer_name
        }
    
    def extract_first_datasheet_url(self, search_response: Dict[str, Any]) -> Optional[str]:
        """Legacy method - extract just the URL. Use extract_first_datasheet_info for more info."""
        info = self.extract_first_datasheet_info(search_response)
        return info["url"] if info else None

    def download_pdf(self, url: str, manufacturer: Optional[str] = None, target_folder: Optional[Path] = None) -> Path:
        """Download a PDF from `url` and save it under `settings.DATASHEET_FOLDER`.
        
        Args:
            url: URL to download PDF from
            manufacturer: Manufacturer name to prefix the filename (for better detection)
            target_folder: Optional target folder (defaults to settings.DATASHEET_FOLDER)

        Returns the saved Path.
        """
        if not url or not url.startswith("http"):
            raise DigiKeyException("Invalid URL to download")

        target_folder = Path(settings.DATASHEET_FOLDER)
        target_folder.mkdir(parents=True, exist_ok=True)

        # Use last segment as filename if possible
        filename = url.split("/")[-1].split("?")[0]
        if not filename.lower().endswith(".pdf"):
            filename = filename + ".pdf"
        
        # Prefix with manufacturer for easier detection
        if manufacturer:
            # Normalize manufacturer name for filename
            mfr_prefix = self._normalize_manufacturer_name(manufacturer)
            filename = f"{mfr_prefix}_{filename}"

        local_path = target_folder / filename

        # Stream download
        with requests.get(url, stream=True, timeout=30) as r:
            if r.status_code != 200:
                logger.error("Failed to download PDF: %s %s", r.status_code, r.text[:200])
                raise DigiKeyException(f"Failed to download PDF: {r.status_code}")

            with local_path.open("wb") as fh:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        fh.write(chunk)

        return local_path
    
    def _normalize_manufacturer_name(self, manufacturer: str) -> str:
        """Normalize manufacturer name for use in filenames.
        
        Maps common manufacturer names to standard codes:
        - STMicroelectronics -> STM
        - Texas Instruments -> TI
        - onsemi -> ONSEMI
        - etc.
        """
        if not manufacturer:
            return "UNKNOWN"
        
        mfr_lower = manufacturer.lower()
        
        # Map to standard manufacturer codes
        if "stmicro" in mfr_lower or "st.com" in mfr_lower:
            return "STM"
        elif "texas" in mfr_lower or "ti.com" in mfr_lower:
            return "TI"
        elif "onsemi" in mfr_lower:
            return "ONSEMI"
        elif "nxp" in mfr_lower:
            return "NXP"
        elif "analog" in mfr_lower:
            return "ANALOG_DEVICES"
        else:
            # Use first word of manufacturer name, sanitized
            return manufacturer.split()[0].upper().replace(",", "").replace(".", "")


digi_service = DigiKeyService()


def search_and_download_datasheet(keyword: str) -> Dict[str, Any]:
    """Convenience wrapper: search by keyword and download first datasheet PDF.

    Returns dict with 'path' (local Path) and 'manufacturer' (str).
    """
    resp = digi_service.search_keyword(keyword)
    info = digi_service.extract_first_datasheet_info(resp)
    if not info:
        raise DigiKeyException("No datasheet URL found in search response")

    path = digi_service.download_pdf(info["url"], manufacturer=info["manufacturer"])
    
    return {
        "path": path,
        "manufacturer": info["manufacturer"]
    }
