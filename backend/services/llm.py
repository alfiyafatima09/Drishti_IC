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
        
        self.prompt = """
        You are an expert in all IC package types, especially DIP, SOIC, and TSSOP packages where pins exist only on two opposite long sides.

IMPORTANT:
- Detect whether the IC has pins on only two sides (DIP/SOIC style) or on all four sides (QFN/QFP).
- If the chip has pins ONLY on two opposite long sides, then you MUST count only those two sides and ignore the other two sides entirely.

Instructions:
1. Identify how many sides actually have pins. If only two opposite sides have pins (as in a DIP or SOIC), then:
   - Count the pins on the left side.
   - Count the pins on the right side.
2. Add left-side pins + right-side pins to get the total pin count.
3. Do NOT assume 4-sided pins if they are not present.
4. Do NOT count shadows, bevels, or edges of the package as pins.

CRITICAL:
Your final output must be ONLY the total pin count as a single integer.
No extra words. No explanation. No symbols.

Output format:
<total_pin_count>
        """

        # self.prompt = (
        #     "You are given an image of an electronic IC chip. "
        #     "Analyze the image and identify:\n"
        #     "1. The manufacturer name of the chip from the logo\n"
        #     "2. The total number of pins\n\n"
        #     "Respond ONLY in JSON format with no additional text:\n"
        #     '{"manufacturer": "<manufacturer_name>", "pin_count": <number>}'
        # )

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

        # Try reducing quality first (95 -> min_quality)
        for quality in range(95, self.min_quality - 1, -5):
            buf = io.BytesIO()
            img.save(buf, format='JPEG', quality=quality, optimize=True)
            size_kb = buf.tell() / 1024

            if size_kb <= self.target_kb:
                return buf.getvalue()

            last_data = buf.getvalue()

        # If quality reduction not enough, progressively downscale
        scale_factor = 0.9
        w, h = img.size
        min_dimension = 50

        for _ in range(8):  # max 8 iterations
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

        # Fallback: return last attempt (may exceed target)
        if last_data:
            return last_data

        raise ValueError(f"Failed to compress image to target size")

    def _parse_response(self, response_text: str) -> Dict[str, Optional[str]]:
        """
        Parse manufacturer and pin_count from API response.

        Tries multiple strategies:
        1. Strict JSON parsing
        2. Regex-based JSON extraction
        3. Heuristics for fallback

        Args:
            response_text: Raw API response text.

        Returns:
            Dict with "manufacturer" and "pin_count" keys.
        """
        result = {"manufacturer": "", "pin_count": ""}

        if not response_text:
            return result

        # Strategy 1: Strict JSON parse
        try:
            doc = json.loads(response_text)
            if isinstance(doc, dict):
                result["manufacturer"] = str(doc.get("manufacturer", "")).strip()
                result["pin_count"] = str(doc.get("pin_count", "")).strip()
                if result["manufacturer"] or result["pin_count"]:
                    return result
        except json.JSONDecodeError:
            pass

        # Strategy 2: Extract JSON substring
        try:
            match = re.search(r'\{[^{}]*\}', response_text, re.DOTALL)
            if match:
                doc = json.loads(match.group(0))
                if isinstance(doc, dict):
                    result["manufacturer"] = str(doc.get("manufacturer", "")).strip()
                    result["pin_count"] = str(doc.get("pin_count", "")).strip()
                    if result["manufacturer"] or result["pin_count"]:
                        return result
        except (json.JSONDecodeError, AttributeError):
            pass

        # Strategy 3: Heuristic extraction for pin_count
        if not result["pin_count"]:
            # Look for "X pins" or "X-pin"
            match = re.search(
                r'(\d{1,3})\s*(?:pins?|pin)',
                response_text,
                re.IGNORECASE
            )
            if match:
                result["pin_count"] = match.group(1)
            else:
                # Look for any 2-3 digit number
                numbers = re.findall(r'\b(\d{1,3})\b', response_text)
                if numbers:
                    result["pin_count"] = min(numbers, key=int)

        # Strategy 4: Heuristic extraction for manufacturer
        if not result["manufacturer"]:
            # Look for capitalized brand names
            match = re.search(
                r'([A-Z][A-Za-z0-9&\-]{1,20}(?:\s+[A-Z][A-Za-z0-9&\-]{1,20})?)',
                response_text
            )
            if match:
                result["manufacturer"] = match.group(1).strip()

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
        
        Falls back to dummy response if endpoint is unavailable.

        Args:
            image_path: Path to the image file.

        Returns:
            Dict with keys: "manufacturer" and "pin_count".
            When in fallback mode, also includes "_fallback" and "_debug_message".

        Raises:
            ValueError: If image processing fails.
        """
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
            result = self._parse_response(response_text)

            return result
            
        except requests.exceptions.RequestException as e:
            print(f"Vision API request failed: {e}. Using fallback response.")
            return self._get_fallback_response()
        except Exception as e:
            raise ValueError(f"Image processing failed: {e}")
    