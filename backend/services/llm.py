"""
LLM service for vision-based IC chip analysis.
"""
import base64
import io
import json
import re
from typing import Dict, Optional
from dotenv import load_dotenv
import requests
from PIL import Image
import os

load_dotenv()

BASE_URL = os.getenv("LLM_BASE_URL")
class LLM:
    """Vision API client for analyzing IC chip images."""

    def __init__(
        self,
        endpoint: str = BASE_URL + "/api/v1/vision/upload",
        temperature: float = 0.8,
        max_tokens: int = 4096,
        target_kb: int = 60,
        min_quality: int = 20,
        timeout: int = 60,
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

        # Simplified user prompt to avoid conflict with system prompt
        self.prompt = "Extract IC details." # System prompt in local_model/prompts.py handles the strict formatting

    def compress_image(self, image_path: str) -> bytes:
        """
        Compress image to target size (<60KB).

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

        last_data = None

        for quality in range(95, self.min_quality - 1, -5):
            buf = io.BytesIO()
            img.save(buf, format='JPEG', quality=quality, optimize=True)
            size_kb = buf.tell() / 1024

            if size_kb <= self.target_kb:
                return buf.getvalue()

            last_data = buf.getvalue()

        scale_factor = 0.9
        w, h = img.size
        min_dimension = 50

        for _ in range(8):  
            w = int(w * scale_factor)
            h = int(h * scale_factor)

            if w < min_dimension or h < min_dimension:
                break

            img_scaled = img.resize((w, h), Image.LANCZOS)

            for quality in range(85, self.min_quality - 1, -5):
                buf = io.BytesIO()
                img_scaled.save(buf, format='JPEG', quality=quality, optimize=True)
                size_kb = buf.tell() / 1024

                if size_kb <= self.target_kb:
                    return buf.getvalue()

                last_data = buf.getvalue()

        if last_data:
            return last_data

        raise ValueError(f"Failed to compress image to target size")

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

        upper_mfg = manufacturer.upper().strip()

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

        if upper_mfg in manufacturer_map:
            return manufacturer_map[upper_mfg]

        for abbr, full_name in manufacturer_map.items():
            if abbr in upper_mfg:
                return full_name

        return manufacturer

    def _parse_response(self, response_text: str) -> Dict[str, Optional[str]]:
        """
        Parse manufacturer, pin_count, and part_number from API response.

        Args:
            response_text: Raw API response text.

        Returns:
            Dict with "manufacturer" and "pin_count" keys.
        """
        result = {"manufacturer": "", "pin_count": ""}

        if not response_text:
            return result

        try:
            data = json.loads(response_text)
        except json.JSONDecodeError:
            data = {}

        if isinstance(data, dict):
            if "response" in data and isinstance(data["response"], str):
                try:
                    inner_data = json.loads(data["response"])
                    if isinstance(inner_data, dict):
                        data = inner_data
                except json.JSONDecodeError:
                    pass
            elif "content" in data and isinstance(data["content"], str):
                try:
                    inner_data = json.loads(data["content"])
                    if isinstance(inner_data, dict):
                        data = inner_data
                except json.JSONDecodeError:
                    pass

        if not data:
             try:
                match = re.search(r'\{[^{}]*\}', response_text, re.DOTALL)
                if match:
                    data = json.loads(match.group(0))
             except (json.JSONDecodeError, AttributeError):
                 data = {}

        if isinstance(data, dict):
            manufacturer = data.get("logo") or data.get("manufacturer") or ""
            manufacturer = str(manufacturer).strip()
            
            if manufacturer.lower() == "unknown":
                result["manufacturer"] = "Unknown"
            else:
                result["manufacturer"] = self._normalize_manufacturer(manufacturer)
            
            result["pin_count"] = str(data.get("num_pins") or data.get("pin_count") or "0").strip()
            result["part_number"] = str(data.get("part_number", "")).strip()

        return result

    def _get_fallback_response(self) -> Dict[str, Optional[str]]:
        """
        Return a dummy fallback response when vision API fails.
        
        Returns:
            Dict with dummy values indicating fallback mode.
        """
        return {
            "manufacturer": "TI",
            "pin_count": "14",
            "_fallback": True,
            "_debug_message": "Vision endpoint unavailable - using fallback dummy response"
        }

    def analyze_image(self, image_path: str) -> Dict[str, Optional[str]]:
        """
        Compress and analyze an IC chip image.
        
        Args:
            image_path: Path to the image file.

        Returns:
            Dict with keys: "manufacturer" and "pin_count". "part_number" is also included.

        Raises:
            ValueError: If image processing fails.
        """
        try:
            compressed_data = self.compress_image(image_path)

            files = {
                "image": ("image.jpg", compressed_data, "image/jpeg"),
                "prompt": (None, self.prompt),
                "max_tokens": (None, str(self.max_tokens)),
                "temperature": (None, str(self.temperature)),
            }

            response = requests.post(
                self.endpoint,
                files=files,
                timeout=self.timeout,
            )
            response.raise_for_status()

            response_text = response.text
            print(f"DEBUG: Raw LLM Response: {response_text}")
            result = self._parse_response(response_text)

            return result
            
        except requests.exceptions.RequestException as e:
            print(f"Vision API request failed: {e}. Using fallback response.")
            return self._get_fallback_response()
        except Exception as e:
            raise ValueError(f"Image processing failed: {e}")