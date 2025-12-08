"""
LLM service for vision-based IC chip analysis.
"""
import base64
import io
import json
import re
import logging
from typing import Dict, Optional
from dotenv import load_dotenv
import requests
from PIL import Image
import os
from pathlib import Path

load_dotenv()

logger = logging.getLogger(__name__)

BASE_URL = os.getenv("LLM_BASE_URL")
LOCAL_MODEL_URL = os.getenv("LOCAL_MODEL_URL", "http://localhost:8001")
class LLM:
    """Vision API client for analyzing IC chip images."""

    def __init__(
        self,
        endpoint: Optional[str] = None,
        use_local_model: bool = True,
        temperature: float = 0.8,
        max_tokens: int = 512,  # Reduced for faster inference
        target_kb: int = 30,  # Reduced from 60KB to 30KB for faster processing
        min_quality: int = 20,
        timeout: int = 300,  # Increased timeout for CPU processing
    ):
        """
        Initialize the LLM vision API client.

        Args:
            endpoint: Vision API endpoint URL (optional, overrides use_local_model).
            use_local_model: If True, use local model endpoint. If False, use BASE_URL.
            temperature: Sampling temperature (0.0-1.0).
            max_tokens: Maximum tokens in response.
            target_kb: Target image size in KB for compression.
            min_quality: Minimum JPEG quality to try.
            timeout: Request timeout in seconds.
        """
        if endpoint:
            self.endpoint = endpoint
            self.use_local_model = False
        elif use_local_model:
            self.endpoint = f"{LOCAL_MODEL_URL}/api/v1/vision/upload"
            self.use_local_model = True
        else:
            if BASE_URL:
                self.endpoint = BASE_URL + "/api/vision"
                self.use_local_model = False
            else:
                # Fallback to local model if BASE_URL not set
                self.endpoint = f"{LOCAL_MODEL_URL}/api/v1/vision/upload"
                self.use_local_model = True
        
        if not self.endpoint:
            raise ValueError("Either endpoint, BASE_URL, or LOCAL_MODEL_URL must be set")
        
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.target_kb = target_kb
        self.min_quality = min_quality
        self.timeout = timeout
        
        self.prompt = """
You are an expert Integrated Circuit (IC) Inspection Agent.
Analyze the image and extract the following details into a JSON object:

1. "texts": All visible alphanumeric markings, row by row.
2. "logo": The manufacturer name if a logo is visible (e.g., TI, ST, Microchip, Atmel). If unknown, use "unknown".
3. "num_pins": Total number of pins/leads visible. If no pins are clearly visible (e.g. top view of QFN) or if you are unsure, return 0.

IMPORTANT for pin counting:
- Detect whether the IC has pins on only two sides (DIP/SOIC style) or on all four sides (QFN/QFP).
- If the chip has pins ONLY on two opposite long sides, then you MUST count only those two sides and ignore the other two sides entirely.
- Do NOT count shadows, bevels, or edges of the package as pins.
- If you are unsure or cannot see pins clearly, strictly return 0.
- If the detected manufacturer is "TI", you MUST expand it to "Texas Instruments".

Output Format (JSON Only):
{
  "texts": ["Part Number", "Date Code", "trace codes"],
  "logo": "Manufacturer Name",
  "num_pins": 14
}

Strictly NO Markdown, NO explanations, ONLY raw JSON.
        """

    def compress_image(self, image_path: str) -> bytes:
        """
        Compress and resize image to target size for faster CPU processing.

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

        # First, resize to max 800px on longest side for faster processing
        max_size = 800
        w, h = img.size
        if w > max_size or h > max_size:
            if w > h:
                new_w = max_size
                new_h = int(h * (max_size / w))
            else:
                new_h = max_size
                new_w = int(w * (max_size / h))
            img = img.resize((new_w, new_h), Image.LANCZOS)
            logger.debug(f"Resized image from {w}x{h} to {new_w}x{new_h}")

        last_data = None

        # Try reducing quality first (85 -> min_quality, step by 10 for speed)
        for quality in range(85, self.min_quality - 1, -10):
            buf = io.BytesIO()
            img.save(buf, format='JPEG', quality=quality, optimize=True)
            size_kb = buf.tell() / 1024

            if size_kb <= self.target_kb:
                logger.debug(f"Compressed to {size_kb:.1f}KB at quality {quality}")
                return buf.getvalue()

            last_data = buf.getvalue()

        # If quality reduction not enough, downscale more aggressively
        scale_factor = 0.8
        w, h = img.size
        min_dimension = 200  # Increased from 50 to maintain quality

        for _ in range(3):  # Reduced from 8 to 3 iterations
            w = int(w * scale_factor)
            h = int(h * scale_factor)

            if w < min_dimension or h < min_dimension:
                break

            img_scaled = img.resize((w, h), Image.LANCZOS)

            for quality in range(75, self.min_quality - 1, -10):
                buf = io.BytesIO()
                img_scaled.save(buf, format='JPEG', quality=quality, optimize=True)
                size_kb = buf.tell() / 1024

                if size_kb <= self.target_kb:
                    logger.debug(f"Compressed to {size_kb:.1f}KB at {w}x{h}, quality {quality}")
                    return buf.getvalue()

                last_data = buf.getvalue()

        # Fallback: return last attempt (may exceed target)
        if last_data:
            logger.debug(f"Using fallback compression: {len(last_data)/1024:.1f}KB")
            return last_data

        raise ValueError(f"Failed to compress image to target size")

    def _parse_response(self, response_text: str) -> Dict[str, Optional[str]]:
        """
        Parse manufacturer and pin_count from API response.

        Supports both local model format (num_pins, logo) and legacy format (pin_count, manufacturer).
        Tries multiple strategies:
        1. Strict JSON parsing (handles both formats)
        2. Regex-based JSON extraction
        3. Heuristics for fallback

        Args:
            response_text: Raw API response text.

        Returns:
            Dict with "manufacturer" and "pin_count" keys.
        """
        result = {"manufacturer": "", "pin_count": "0"}

        if not response_text:
            return result

        # Strategy 1: Strict JSON parse (handles both local model and legacy formats)
        try:
            doc = json.loads(response_text)
            if isinstance(doc, dict):
                # Local model format: num_pins, logo
                if "num_pins" in doc:
                    val = doc.get("num_pins")
                    result["pin_count"] = "0" if val is None else str(val).strip()
                # Legacy format: pin_count
                elif "pin_count" in doc:
                    val = doc.get("pin_count")
                    result["pin_count"] = "0" if val is None else str(val).strip()
                
                # Local model format: logo
                if "logo" in doc:
                    logo_value = str(doc.get("logo", "")).strip()
                    if logo_value and logo_value.lower() != "unknown":
                        result["manufacturer"] = logo_value
                # Legacy format: manufacturer
                elif "manufacturer" in doc:
                    result["manufacturer"] = str(doc.get("manufacturer", "")).strip()
                
                if result["manufacturer"] or result["pin_count"] != "0":
                    return result
        except json.JSONDecodeError:
            pass

        # Strategy 2: Extract JSON substring
        try:
            match = re.search(r'\{[^{}]*\}', response_text, re.DOTALL)
            if match:
                doc = json.loads(match.group(0))
                if isinstance(doc, dict):
                    # Local model format
                    if "num_pins" in doc:
                        val = doc.get("num_pins")
                        result["pin_count"] = "0" if val is None else str(val).strip()
                    elif "pin_count" in doc:
                        val = doc.get("pin_count")
                        result["pin_count"] = "0" if val is None else str(val).strip()
                    
                    if "logo" in doc:
                        logo_value = str(doc.get("logo", "")).strip()
                        if logo_value and logo_value.lower() != "unknown":
                            result["manufacturer"] = logo_value
                    elif "manufacturer" in doc:
                        result["manufacturer"] = str(doc.get("manufacturer", "")).strip()
                    
                    if result["manufacturer"] or result["pin_count"] != "0":
                        return result
        except (json.JSONDecodeError, AttributeError):
            pass

        # Strategy 3: Heuristic extraction for pin_count
        # Only try heuristics if we haven't found a valid count yet
        if result["pin_count"] == "0":
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
                # CAUTION: This is risky if there are other numbers. 
                # Only use if we are reasonably sure it is a pin count (e.g. smallish number)
                numbers = re.findall(r'\b(\d{1,3})\b', response_text)
                if numbers:
                    # Prefer numbers that look like pin counts (e.g. even numbers, typical sizes)
                    # But for now just taking the smallest might be too aggressive if it's "2023" date code
                    # Let's trust the model's explicit output more often.
                    # If we really found nothing, stick with 0.
                    pass

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

    def analyze_image(self, image_path: str) -> Dict[str, Optional[str]]:
        """
        Compress and analyze an IC chip image.

        Args:
            image_path: Path to the image file.

        Returns:
            Dict with keys: "manufacturer" and "pin_count".

        Raises:
            ValueError: If image processing fails.
            requests.RequestException: If API request fails.
        """
        # Compress image
        compressed_data = self.compress_image(image_path)

        if self.use_local_model:
            # Local model endpoint expects form data with file upload
            image_filename = Path(image_path).name if image_path else "image.jpg"
            files = {
                "image": (image_filename, compressed_data, "image/jpeg")
            }
            data = {
                "prompt": self.prompt,
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
            }
            
            response = requests.post(
                self.endpoint,
                files=files,
                data=data,
                timeout=self.timeout,
            )
            response.raise_for_status()
            
            # Local model returns JSON with "response" and "model" fields
            response_data = response.json()
            response_text = response_data.get("response", "")
        else:
            # Legacy endpoint expects JSON with base64
            image_base64 = base64.b64encode(compressed_data).decode('ascii')
            payload = {
                "prompt": self.prompt,
                "image_base64": image_base64,
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
            }
            
            headers = {"Content-Type": "application/json"}
            response = requests.post(
                self.endpoint,
                json=payload,
                headers=headers,
                timeout=self.timeout,
            )
            response.raise_for_status()
            response_text = response.text

        # Parse response
        result = self._parse_response(response_text)

        return result
    