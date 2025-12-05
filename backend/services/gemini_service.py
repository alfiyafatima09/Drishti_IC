# """
# Gemini AI Service for IC Analysis.
# Handles OCR text extraction and pin count detection using Google's Gemini API.
# """
# import logging
# import google.generativeai as genai
# from pathlib import Path
# from typing import Tuple, Dict, Any
# import json
# import re

# from core.config import settings
# from schemas.ic_analysis import OCRTextData, PinDetectionData

# logger = logging.getLogger(__name__)


# class GeminiServiceException(Exception):
#     """Exception raised when Gemini API calls fail."""
#     pass


# class GeminiICAnalysisService:
#     """Service for analyzing IC chips using Gemini AI."""
    
#     def __init__(self):
#         """Initialize Gemini API with the API key."""
#         if not settings.GEMINI_API_KEY:
#             raise GeminiServiceException(
#                 "GEMINI_API_KEY not configured. Please add it to your .env file."
#             )
        
#         genai.configure(api_key=settings.GEMINI_API_KEY)
#         self.model = genai.GenerativeModel('gemini-2.5-flash')
#         logger.info("Gemini AI service initialized successfully")
    
#     def _parse_ocr_response(self, response_text: str) -> Dict[str, Any]:
#         """
#         Parse Gemini's OCR response to extract structured data.
        
#         Args:
#             response_text: Raw response from Gemini
            
#         Returns:
#             Dictionary with parsed OCR data
#         """
#         try:
#             # Try to parse as JSON if Gemini returns structured data
#             # Remove markdown code blocks if present
#             clean_text = response_text.strip()
#             if "```json" in clean_text:
#                 clean_text = clean_text.split("```json")[1].split("```")[0].strip()
#             elif "```" in clean_text:
#                 clean_text = clean_text.split("```")[1].split("```")[0].strip()
            
#             try:
#                 data = json.loads(clean_text)
#                 return data
#             except json.JSONDecodeError:
#                 # Fallback: parse as plain text
#                 logger.warning("Could not parse JSON response, using text parsing")
#                 return self._parse_text_ocr(response_text)
                
#         except Exception as e:
#             logger.error(f"Error parsing OCR response: {e}")
#             return self._parse_text_ocr(response_text)
    
#     def _parse_text_ocr(self, text: str) -> Dict[str, Any]:
#         """Fallback text parser for OCR data."""
#         lines = [line.strip() for line in text.split('\n') if line.strip()]
        
#         # Basic heuristics to extract data
#         part_number = None
#         manufacturer = None
#         date_code = None
        
#         for line in lines:
#             # Look for common IC patterns
#             if re.search(r'[A-Z]{2,}\d{2,}', line) and not part_number:
#                 part_number = line
#             elif any(mfr in line.upper() for mfr in ['TEXAS', 'STM', 'INTEL', 'TI', 'MICROCHIP']):
#                 manufacturer = line
#             elif re.search(r'\d{4}\s*\d{2}', line):
#                 date_code = line
        
#         return {
#             "raw_text": text,
#             "part_number": part_number,
#             "manufacturer": manufacturer,
#             "date_code": date_code,
#             "lot_code": None,
#             "other_markings": lines[3:] if len(lines) > 3 else [],
#             "confidence_score": 75.0  # Default confidence for text parsing
#         }
    
#     def _parse_pin_response(self, response_text: str) -> Dict[str, Any]:
#         """
#         Parse Gemini's pin detection response.
        
#         Args:
#             response_text: Raw response from Gemini
            
#         Returns:
#             Dictionary with parsed pin data
#         """
#         try:
#             # Try JSON parsing first
#             clean_text = response_text.strip()
#             if "```json" in clean_text:
#                 clean_text = clean_text.split("```json")[1].split("```")[0].strip()
#             elif "```" in clean_text:
#                 clean_text = clean_text.split("```")[1].split("```")[0].strip()
            
#             try:
#                 data = json.loads(clean_text)
#                 return data
#             except json.JSONDecodeError:
#                 logger.warning("Could not parse JSON response, using text parsing for pins")
#                 return self._parse_text_pins(response_text)
                
#         except Exception as e:
#             logger.error(f"Error parsing pin response: {e}")
#             return self._parse_text_pins(response_text)
    
#     def _parse_text_pins(self, text: str) -> Dict[str, Any]:
#         """Fallback text parser for pin detection."""
#         # Look for numbers in the response
#         numbers = re.findall(r'\b(\d+)\b', text)
#         pin_count = int(numbers[0]) if numbers else 0
        
#         # Look for package type mentions
#         package_type = None
#         package_keywords = {
#             'DIP': 'DIP',
#             'SOIC': 'SOIC',
#             'QFN': 'QFN',
#             'BGA': 'BGA',
#             'TSSOP': 'TSSOP',
#             'QFP': 'QFP',
#         }
        
#         for keyword, ptype in package_keywords.items():
#             if keyword in text.upper():
#                 package_type = ptype
#                 break
        
#         return {
#             "pin_count": pin_count,
#             "package_type": package_type,
#             "pin_layout": f"Detected {pin_count} pins" if pin_count > 0 else "Unable to detect pins",
#             "confidence_score": 70.0,
#             "detection_method": "Gemini Vision Analysis (Text Parsing)"
#         }
    
#     async def extract_text(self, image_path: Path) -> OCRTextData:
#         """
#         Extract all visible text from IC chip image using Gemini.
        
#         Args:
#             image_path: Path to the IC image
            
#         Returns:
#             OCRTextData with extracted information
            
#         Raises:
#             GeminiServiceException: If text extraction fails
#         """
#         try:
#             logger.info(f"Extracting text from image: {image_path}")
            
#             # Upload the image to Gemini
#             uploaded_file = genai.upload_file(path=str(image_path))
            
#             # Craft prompt for OCR
#             prompt = """
# Analyze this integrated circuit (IC) chip image and extract ALL visible text.

# Please provide the information in the following JSON format:
# {
#   "raw_text": "all text you can see, line by line",
#   "part_number": "the IC part number (e.g., LM555, STM32F407)",
#   "manufacturer": "manufacturer name if visible (e.g., Texas Instruments, STMicroelectronics)",
#   "date_code": "date/week code if visible (e.g., 2023 43)",
#   "lot_code": "lot or batch code if visible",
#   "other_markings": ["any other visible text or markings"],
#   "confidence_score": 85.0
# }

# Be thorough and extract every piece of text you can see on the chip. If you're unsure about any field, set it to null.
# """
            
#             response = self.model.generate_content([prompt, uploaded_file])
#             response_text = response.text
            
#             logger.info(f"Gemini OCR response: {response_text[:200]}...")
            
#             # Parse the response
#             parsed_data = self._parse_ocr_response(response_text)
            
#             # Create OCRTextData object
#             ocr_data = OCRTextData(**parsed_data)
            
#             # Clean up uploaded file
#             genai.delete_file(uploaded_file.name)
            
#             return ocr_data
            
#         except Exception as e:
#             logger.error(f"Error extracting text with Gemini: {e}")
#             raise GeminiServiceException(f"Failed to extract text: {str(e)}")
    
#     async def detect_pins(self, image_path: Path) -> PinDetectionData:
#         """
#         Detect pin count and package type using Gemini Vision.
        
#         Args:
#             image_path: Path to the IC image
            
#         Returns:
#             PinDetectionData with pin information
            
#         Raises:
#             GeminiServiceException: If pin detection fails
#         """
#         try:
#             logger.info(f"Detecting pins in image: {image_path}")
            
#             # Upload the image to Gemini
#             uploaded_file = genai.upload_file(path=str(image_path))
            
#             # Craft prompt for pin detection
#             prompt = """
# Analyze this integrated circuit (IC) chip image and count the pins/leads.

# Please provide the information in the following JSON format:
# {
#   "pin_count": 8,
#   "package_type": "DIP-8 (Dual In-line Package, 8 pins)",
#   "pin_layout": "Dual in-line configuration with 4 pins on each side",
#   "confidence_score": 90.0,
#   "detection_method": "Gemini Vision Analysis"
# }

# Instructions:
# - Count ALL visible pins/leads carefully
# - Identify the package type (DIP, SOIC, QFN, BGA, TSSOP, QFP, etc.)
# - Describe the pin layout
# - For bottom-terminated components (BGA, QFN), mention if pins are not visible from this angle
# - Provide confidence score (0-100) based on visibility and clarity
# """
            
#             response = self.model.generate_content([prompt, uploaded_file])
#             response_text = response.text
            
#             logger.info(f"Gemini pin detection response: {response_text[:200]}...")
            
#             # Parse the response
#             parsed_data = self._parse_pin_response(response_text)
            
#             # Create PinDetectionData object
#             pin_data = PinDetectionData(**parsed_data)
            
#             # Clean up uploaded file
#             genai.delete_file(uploaded_file.name)
            
#             return pin_data
            
#         except Exception as e:
#             logger.error(f"Error detecting pins with Gemini: {e}")
#             raise GeminiServiceException(f"Failed to detect pins: {str(e)}")
    
#     async def analyze_ic(self, image_path: Path) -> Tuple[OCRTextData, PinDetectionData]:
#         """
#         Complete IC analysis: extract text and detect pins.
        
#         Args:
#             image_path: Path to the IC image
            
#         Returns:
#             Tuple of (OCRTextData, PinDetectionData)
            
#         Raises:
#             GeminiServiceException: If analysis fails
#         """
#         try:
#             # Run both analyses
#             ocr_data = await self.extract_text(image_path)
#             pin_data = await self.detect_pins(image_path)
            
#             return ocr_data, pin_data
            
#         except Exception as e:
#             logger.error(f"Error in IC analysis: {e}")
#             raise GeminiServiceException(f"IC analysis failed: {str(e)}")


# # Global service instance
# gemini_service = GeminiICAnalysisService()
