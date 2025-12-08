"""
LLM service for vision-based IC chip analysis.
"""
import base64
import io
import json
import re
import hashlib
import time
from typing import Dict, Optional, Tuple
from functools import lru_cache
from dotenv import load_dotenv
import requests
from PIL import Image
import os

load_dotenv()

BASE_URL = os.getenv("LLM_BASE_URL")

# Simple in-memory cache for LLM responses
_llm_cache: Dict[str, Tuple[Dict[str, str], float]] = {}
CACHE_TTL = 3600  # 1 hour cache TTL


def _get_image_hash(image_path: str) -> str:
    """Generate hash of image file for caching."""
    hash_md5 = hashlib.md5()
    with open(image_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def _get_cached_result(cache_key: str) -> Optional[Dict[str, str]]:
    """Get cached result if still valid."""
    if cache_key in _llm_cache:
        result, timestamp = _llm_cache[cache_key]
        if time.time() - timestamp < CACHE_TTL:
            return result
        else:
            # Remove expired cache entry
            del _llm_cache[cache_key]
    return None


def _set_cached_result(cache_key: str, result: Dict[str, str]):
    """Cache the result."""
    _llm_cache[cache_key] = (result, time.time())


def clear_llm_cache():
    """Clear the LLM response cache."""
    global _llm_cache
    _llm_cache.clear()
class LLM:
    """Vision API client for analyzing IC chip images."""

    def __init__(
        self,
        endpoint: str = BASE_URL + "/api/v1/vision/upload",
        temperature: float = 0.1,  # Reduced from 0.8 for faster, more consistent responses
        max_tokens: int = 256,    # Reduced from 4096 for faster processing
        target_kb: int = 40,      # Reduced from 60KB for faster compression
        min_quality: int = 30,    # Increased from 20 for better quality/speed balance
        timeout: int = 30,        # Reduced from 60 seconds
    ):
        """
        Initialize the LLM vision API client.

        Args:
            endpoint: Vision API endpoint URL.
            temperature: Sampling temperature (0.0-1.0).
            max_tokens: Maximum tokens in response.
            target_kb: Target image size in KB for compression.
            min_quality: Minimum JPEG quality to try.
            timeout: Request timeout in seconds.
        """
        self.endpoint = endpoint
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.target_kb = target_kb
        self.min_quality = min_quality
        self.timeout = timeout

        self.prompt = (
            "Analyze this IC chip image and identify:\n"
            "1. The manufacturer (company name)\n"
            "2. The total number of pins visible on the chip\n\n"
            "Look for:\n"
            "- Manufacturer logos or markings (TI, STM, ATMEL, etc.)\n"
            "- Physical pins around the edges of the chip\n\n"
            "Return ONLY valid JSON:\n"
            '{"manufacturer": "Texas Instruments", "pin_count": 8}'
        )

    def compress_image(self, image_path: str) -> bytes:
        """
        Compress image to target size (<40KB) - Optimized for speed.

        Args:
            image_path: Path to the image file.

        Returns:
            Compressed image bytes.

        Raises:
            ValueError: If image cannot be opened or compressed.
        """
        try:
            img = Image.open(image_path).convert('RGB')
        except Exception as e:
            raise ValueError(f"Failed to open image {image_path}: {e}")

        # Fast compression: try quality levels with larger steps
        for quality in [80, 60, 40]:  # Fewer quality levels for speed
            buf = io.BytesIO()
            img.save(buf, format='JPEG', quality=quality, optimize=True)
            size_kb = buf.tell() / 1024

            if size_kb <= self.target_kb:
                return buf.getvalue()

        # If still too large, resize image
        w, h = img.size
        scale_factor = 0.8
        for _ in range(3):  # Max 3 resize attempts
            w = int(w * scale_factor)
            h = int(h * scale_factor)

            if w < 100 or h < 100:  # Minimum size
                break

            img_resized = img.resize((w, h), Image.LANCZOS)
            buf = io.BytesIO()
            img_resized.save(buf, format='JPEG', quality=50, optimize=True)
            size_kb = buf.tell() / 1024

            if size_kb <= self.target_kb:
                return buf.getvalue()

        # Return best attempt
        buf = io.BytesIO()
        img.save(buf, format='JPEG', quality=self.min_quality, optimize=True)
        return buf.getvalue()

    def _parse_response(self, response_text: str) -> Dict[str, Optional[str]]:
        """
        Parse manufacturer and pin_count from API response.
        Enhanced parsing with better error handling.

        Args:
            response_text: Raw API response text.

        Returns:
            Dict with "manufacturer" and "pin_count" keys.
        """
        result = {"manufacturer": "", "pin_count": ""}

        if not response_text or not response_text.strip():
            return result

        # Clean the response text
        response_text = response_text.strip()
        
        # Strategy 1: Parse the API response wrapper first
        try:
            # Parse the full API response
            api_response = json.loads(response_text)
            if isinstance(api_response, dict) and "response" in api_response:
                # Extract the inner response content
                inner_content = api_response["response"]
                if isinstance(inner_content, str):
                    # Try to parse the inner JSON
                    try:
                        inner_data = json.loads(inner_content)
                        if isinstance(inner_data, dict):
                            result["manufacturer"] = str(inner_data.get("manufacturer", "")).strip()
                            result["pin_count"] = str(inner_data.get("pin_count", "")).strip()
                            # Validate we got actual data
                            if result["manufacturer"] or result["pin_count"]:
                                # Apply manufacturer normalization
                                result["manufacturer"] = self._normalize_manufacturer(result["manufacturer"])
                                return result
                    except json.JSONDecodeError:
                        # If inner content is not valid JSON, treat it as raw text and parse with regex
                        response_text = inner_content
        except (json.JSONDecodeError, KeyError, TypeError):
            pass
        
        # Strategy 2: Direct JSON parse (fallback for old format)
        try:
            # Try to find JSON in the response
            json_match = re.search(r'\{[^{}]*\}', response_text)
            if json_match:
                doc = json.loads(json_match.group(0))
                if isinstance(doc, dict):
                    result["manufacturer"] = str(doc.get("manufacturer", "")).strip()
                    result["pin_count"] = str(doc.get("pin_count", "")).strip()
                    # Validate we got actual data
                    if result["manufacturer"] or result["pin_count"]:
                        # Apply manufacturer normalization
                        result["manufacturer"] = self._normalize_manufacturer(result["manufacturer"])
                        return result
        except (json.JSONDecodeError, AttributeError):
            pass

        # Strategy 3: Extract individual fields with regex
        # Look for manufacturer patterns
        manufacturer_patterns = [
            r'"manufacturer"\s*:\s*"([^"]+)"',
            r'manufacturer["\s]*:[\s"]*([A-Za-z][A-Za-z0-9\s&\-]+)',
        ]
        
        for pattern in manufacturer_patterns:
            match = re.search(pattern, response_text, re.IGNORECASE)
            if match:
                manufacturer = match.group(1).strip()
                if manufacturer and len(manufacturer) > 1:
                    result["manufacturer"] = manufacturer
                    break

        # Look for pin count patterns
        pin_patterns = [
            r'"pin_count"\s*:\s*(\d+)',
            r'pin_count["\s]*:[\s"]*(\d+)',
            r'(\d+)\s*pins?',
            r'pins?\s*[:=]\s*(\d+)',
        ]
        
        for pattern in pin_patterns:
            match = re.search(pattern, response_text, re.IGNORECASE)
            if match:
                try:
                    pin_count = int(match.group(1))
                    if 0 <= pin_count <= 1000:  # Reasonable range
                        result["pin_count"] = str(pin_count)
                        break
                except ValueError:
                    continue

        # Apply manufacturer normalization
        result["manufacturer"] = self._normalize_manufacturer(result["manufacturer"])
        
        return result

    def _normalize_manufacturer(self, manufacturer: str) -> str:
        """
        Normalize manufacturer names to standard full names.
        
        Args:
            manufacturer: Raw manufacturer string from LLM
            
        Returns:
            Normalized manufacturer name
        """
        if not manufacturer:
            return ""
            
        # Convert to uppercase for matching
        upper_mfg = manufacturer.upper().strip()
        
        # Manufacturer mapping for common abbreviations
        manufacturer_map = {
            "TI": "Texas Instruments",
            "TEXAS": "Texas Instruments", 
            "TEXAS INSTRUMENTS": "Texas Instruments",
            "STM": "STMicroelectronics",
            "ST": "STMicroelectronics",
            "STMICROELECTRONICS": "STMicroelectronics",
            "ATMEL": "Microchip Technology",
            "MICROCHIP": "Microchip Technology",
            "MICROCHIP TECHNOLOGY": "Microchip Technology",
            "INTEL": "Intel Corporation",
            "ANALOG": "Analog Devices",
            "ANALOG DEVICES": "Analog Devices",
            "MAXIM": "Maxim Integrated",
            "MAXIM INTEGRATED": "Maxim Integrated",
            "NXP": "NXP Semiconductors",
            "INFINEON": "Infineon Technologies",
            "FREESCALE": "NXP Semiconductors",
            "ON": "ON Semiconductor",
            "ON SEMI": "ON Semiconductor",
            "ON SEMICONDUCTOR": "ON Semiconductor",
            "FAIRCHILD": "ON Semiconductor",
            "NATIONAL": "Texas Instruments",
            "LINEAR": "Analog Devices",
            "VISHAY": "Vishay Intertechnology",
            "ROHM": "ROHM Semiconductor",
            "TOSHIBA": "Toshiba Electronic Devices & Storage Corporation",
            "RENESAS": "Renesas Electronics"
        }
        
        # Try exact match first
        if upper_mfg in manufacturer_map:
            return manufacturer_map[upper_mfg]
            
        # Try partial matches for longer strings
        for abbr, full_name in manufacturer_map.items():
            if abbr in upper_mfg:
                return full_name
                
        # Return original if no mapping found
        return manufacturer

    def _get_fallback_response(self) -> Dict[str, Optional[str]]:
        """
        Return a dummy fallback response when vision API fails.
        
        Returns:
            Dict with dummy values indicating fallback mode.
        """
        return {
            "manufacturer": "Texas Instruments",
            "pin_count": "14",
            "_fallback": True,
            "_debug_message": "Vision endpoint unavailable - using fallback dummy response"
        }

    def analyze_image(self, image_path: str) -> Dict[str, Optional[str]]:
        """
        Compress and analyze an IC chip image with caching.
        
        Falls back to dummy response if endpoint is unavailable.

        Args:
            image_path: Path to the image file.

        Returns:
            Dict with keys: "manufacturer" and "pin_count".
            When in fallback mode, also includes "_fallback" and "_debug_message".

        Raises:
            ValueError: If image processing fails.
        """
        # Check cache first
        cache_key = _get_image_hash(image_path)
        cached_result = _get_cached_result(cache_key)
        if cached_result:
            return cached_result
        
        try:
            # Compress image
            compressed_data = self.compress_image(image_path)

            files = {
                "image": ("image.jpg", compressed_data, "image/jpeg"),
                "prompt": (None, self.prompt),
                "max_tokens": (None, str(self.max_tokens)),
                "temperature": (None, str(self.temperature)),
            }

            # Send request
            response = requests.post(
                self.endpoint,
                files=files,
                timeout=self.timeout,
            )
            response.raise_for_status()

            # Parse response
            response_text = response.text
            print(f"DEBUG: LLM Raw Response: {response_text[:200]}...")  # Debug first 200 chars
            result = self._parse_response(response_text)
            print(f"DEBUG: Parsed Result: {result}")  # Debug parsed result
            
            # Cache the result
            _set_cached_result(cache_key, result)

            return result
            
        except requests.exceptions.RequestException as e:
            print(f"Vision API request failed: {e}. Using fallback response.")
            fallback_result = self._get_fallback_response()
            _set_cached_result(cache_key, fallback_result)  # Cache fallback too
            return fallback_result
        except Exception as e:
            raise ValueError(f"Image processing failed: {e}")
    