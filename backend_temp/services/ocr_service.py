"""
OCR service for text extraction from IC images
"""
import cv2
import numpy as np
import pytesseract
from typing import Dict, List, Any, Optional, Tuple
import re
import logging
from datetime import datetime

from config.settings import settings

logger = logging.getLogger(__name__)


class OCRService:
    """Service for extracting text from IC images using OCR"""

    def __init__(self):
        # Configure Tesseract
        pytesseract.pytesseract.tesseract_cmd = settings.tesseract_cmd

        # IC-specific patterns for validation
        self.ic_patterns = {
            "part_number": [
                r'^[A-Z]{2,4}\d{3,6}[A-Z]?\d*$',  # e.g., STM32F103C8, LM358N
                r'^\d{2,4}[A-Z]+\d+[A-Z]*\d*$',    # e.g., 74HC595, 555CN
                r'^[A-Z]+\d{2,6}[A-Z]*\d*$',      # e.g., PIC16F877A, ATmega328P
            ],
            "manufacturer_code": [
                r'^[A-Z]{2,4}$',  # e.g., STM, TI, NXP, MAX
            ],
            "date_code": [
                r'^\d{4,6}$',     # e.g., 2234 (week 34 of 2022), 20231
                r'^\d{2}[A-Z]\d{2}$',  # e.g., 22A34
            ],
            "lot_code": [
                r'^[A-Z]\d{1,3}[A-Z]?$',  # e.g., A123, B45C
                r'^\d{1,3}[A-Z]$',        # e.g., 123A, 45B
            ]
        }

    async def extract_text(
        self,
        image: np.ndarray,
        regions: Optional[List[Dict[str, Any]]] = None,
        preprocess: bool = True
    ) -> Dict[str, Any]:
        """Extract text from image using OCR"""

        try:
            start_time = datetime.utcnow()

            # Preprocess image if requested
            if preprocess:
                processed_image = self._preprocess_for_ocr(image)
            else:
                processed_image = image

            extracted_text = []

            if regions:
                # Extract text from specific regions
                for region in regions:
                    bbox = region["bbox"]
                    x, y, w, h = bbox

                    # Extract region of interest
                    roi = processed_image[y:y+h, x:x+w]

                    if roi.size > 0:
                        text_result = self._extract_text_from_region(roi, bbox)
                        if text_result["text"].strip():
                            extracted_text.append(text_result)
            else:
                # Extract text from entire image
                text_result = self._extract_text_from_region(processed_image)
                if text_result["text"].strip():
                    extracted_text.append(text_result)

            # Analyze and classify extracted text
            analysis = self._analyze_extracted_text(extracted_text)

            processing_time = (datetime.utcnow() - start_time).total_seconds()

            return {
                "extracted_text": extracted_text,
                "analysis": analysis,
                "processing_time_seconds": processing_time,
                "total_regions_processed": len(extracted_text)
            }

        except Exception as e:
            logger.error(f"Error in OCR extraction: {e}")
            raise

    def _preprocess_for_ocr(self, image: np.ndarray) -> np.ndarray:
        """Preprocess image for better OCR results"""

        # Convert to grayscale if needed
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        # Apply Gaussian blur to reduce noise
        blurred = cv2.GaussianBlur(gray, (3, 3), 0)

        # Enhance contrast using CLAHE
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(blurred)

        # Apply morphological operations to clean up text
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        cleaned = cv2.morphologyEx(enhanced, cv2.MORPH_CLOSE, kernel)

        # Apply thresholding
        _, thresh = cv2.threshold(cleaned, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        return thresh

    def _extract_text_from_region(
        self,
        roi: np.ndarray,
        bbox: Optional[Tuple[int, int, int, int]] = None
    ) -> Dict[str, Any]:
        """Extract text from a specific region"""

        try:
            # Configure Tesseract for better IC text recognition
            config = '--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'

            # Extract text
            text_data = pytesseract.image_to_data(roi, config=config, output_type=pytesseract.Output.DICT)

            # Combine text with confidence filtering
            confident_text = []
            confidences = []

            for i, confidence in enumerate(text_data['conf']):
                if int(confidence) > 60:  # Only high confidence text
                    text = text_data['text'][i].strip()
                    if text:
                        confident_text.append(text)
                        confidences.append(int(confidence))

            combined_text = ' '.join(confident_text)
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0

            return {
                "text": combined_text,
                "confidence": avg_confidence,
                "bbox": bbox,
                "word_count": len(confident_text),
                "individual_words": confident_text
            }

        except Exception as e:
            logger.error(f"Error extracting text from region: {e}")
            return {
                "text": "",
                "confidence": 0,
                "bbox": bbox,
                "error": str(e)
            }

    def _analyze_extracted_text(self, extracted_texts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze extracted text to identify IC components"""

        all_text = ' '.join([item['text'] for item in extracted_texts])
        words = re.findall(r'\b\w+\b', all_text.upper())

        analysis = {
            "potential_part_numbers": [],
            "potential_manufacturer_codes": [],
            "potential_date_codes": [],
            "potential_lot_codes": [],
            "all_extracted_words": words,
            "classification_confidence": {}
        }

        # Classify each word
        for word in words:
            word = word.strip()

            # Check for part numbers
            if self._matches_pattern(word, self.ic_patterns["part_number"]):
                analysis["potential_part_numbers"].append({
                    "text": word,
                    "confidence": self._calculate_pattern_confidence(word, "part_number")
                })

            # Check for manufacturer codes
            if self._matches_pattern(word, self.ic_patterns["manufacturer_code"]):
                analysis["potential_manufacturer_codes"].append({
                    "text": word,
                    "confidence": self._calculate_pattern_confidence(word, "manufacturer_code")
                })

            # Check for date codes
            if self._matches_pattern(word, self.ic_patterns["date_code"]):
                analysis["potential_date_codes"].append({
                    "text": word,
                    "confidence": self._calculate_pattern_confidence(word, "date_code")
                })

            # Check for lot codes
            if self._matches_pattern(word, self.ic_patterns["lot_code"]):
                analysis["potential_lot_codes"].append({
                    "text": word,
                    "confidence": self._calculate_pattern_confidence(word, "lot_code")
                })

        # Calculate overall confidence scores
        analysis["classification_confidence"] = {
            "has_part_number": len(analysis["potential_part_numbers"]) > 0,
            "has_manufacturer_code": len(analysis["potential_manufacturer_codes"]) > 0,
            "has_date_code": len(analysis["potential_date_codes"]) > 0,
            "has_lot_code": len(analysis["potential_lot_codes"]) > 0,
            "total_classified_elements": sum([
                len(analysis["potential_part_numbers"]),
                len(analysis["potential_manufacturer_codes"]),
                len(analysis["potential_date_codes"]),
                len(analysis["potential_lot_codes"])
            ])
        }

        # Sort by confidence
        for key in ["potential_part_numbers", "potential_manufacturer_codes",
                   "potential_date_codes", "potential_lot_codes"]:
            analysis[key].sort(key=lambda x: x["confidence"], reverse=True)

        return analysis

    def _matches_pattern(self, text: str, patterns: List[str]) -> bool:
        """Check if text matches any of the given patterns"""

        for pattern in patterns:
            if re.match(pattern, text):
                return True
        return False

    def _calculate_pattern_confidence(self, text: str, pattern_type: str) -> float:
        """Calculate confidence score for pattern matching"""

        base_confidence = 0.7  # Base confidence for pattern match

        # Adjust based on text characteristics
        if pattern_type == "part_number":
            # Longer part numbers are more likely to be correct
            length_bonus = min(len(text) / 10, 0.2)
            # Alphanumeric mix is good
            has_digits = bool(re.search(r'\d', text))
            has_letters = bool(re.search(r'[A-Z]', text))
            mix_bonus = 0.1 if (has_digits and has_letters) else 0

            return min(base_confidence + length_bonus + mix_bonus, 0.95)

        elif pattern_type == "manufacturer_code":
            # Manufacturer codes are usually 2-4 characters
            optimal_length = 2 <= len(text) <= 4
            length_bonus = 0.1 if optimal_length else 0

            return min(base_confidence + length_bonus, 0.9)

        elif pattern_type == "date_code":
            # Date codes should look like dates
            if re.match(r'^\d{4,6}$', text):
                # Check if it could be a reasonable date code
                try:
                    year = int(text[:2]) + 2000 if len(text) >= 4 else int(text[:2])
                    if 2020 <= year <= 2030:  # Reasonable year range
                        return 0.85
                except:
                    pass

            return base_confidence

        elif pattern_type == "lot_code":
            # Lot codes vary widely
            return base_confidence

        return base_confidence

    async def extract_ic_markings(
        self,
        image: np.ndarray,
        marking_regions: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Extract IC markings with focus on authenticity indicators"""

        # Extract text from image
        ocr_result = await self.extract_text(image, marking_regions)

        # Enhanced analysis for counterfeit detection
        authenticity_analysis = self._analyze_authenticity_markers(ocr_result)

        return {
            **ocr_result,
            "authenticity_analysis": authenticity_analysis
        }

    def _analyze_authenticity_markers(self, ocr_result: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze markers that help determine authenticity"""

        analysis = ocr_result["analysis"]
        all_text = ' '.join(ocr_result["extracted_text"])

        authenticity_markers = {
            "marking_consistency": self._check_marking_consistency(analysis),
            "font_characteristics": self._analyze_font_characteristics(ocr_result["extracted_text"]),
            "spacing_uniformity": self._check_spacing_uniformity(ocr_result["extracted_text"]),
            "character_clarity": self._assess_character_clarity(ocr_result["extracted_text"]),
            "suspicious_patterns": self._detect_suspicious_patterns(all_text)
        }

        # Calculate overall authenticity score
        scores = [
            authenticity_markers["marking_consistency"]["score"],
            authenticity_markers["font_characteristics"]["score"],
            authenticity_markers["spacing_uniformity"]["score"],
            authenticity_markers["character_clarity"]["score"]
        ]

        # Penalize for suspicious patterns
        penalty = len(authenticity_markers["suspicious_patterns"]) * 0.1

        overall_score = max(0, (sum(scores) / len(scores)) - penalty)

        authenticity_markers["overall_authenticity_score"] = overall_score
        authenticity_markers["authenticity_confidence"] = min(overall_score + 0.2, 1.0)  # Add some uncertainty

        return authenticity_markers

    def _check_marking_consistency(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Check if markings are consistent with known IC patterns"""

        score = 0
        reasons = []

        # Check for expected marking components
        has_part_number = len(analysis["potential_part_numbers"]) > 0
        has_manufacturer = len(analysis["potential_manufacturer_codes"]) > 0
        has_date = len(analysis["potential_date_codes"]) > 0

        if has_part_number:
            score += 0.3
            reasons.append("Part number detected")
        else:
            reasons.append("No part number found")

        if has_manufacturer:
            score += 0.2
            reasons.append("Manufacturer code detected")
        else:
            reasons.append("No manufacturer code found")

        if has_date:
            score += 0.2
            reasons.append("Date code detected")
        else:
            reasons.append("No date code found")

        # Bonus for having all three
        if has_part_number and has_manufacturer and has_date:
            score += 0.3
            reasons.append("Complete marking set present")

        return {
            "score": min(score, 1.0),
            "reasons": reasons
        }

    def _analyze_font_characteristics(self, extracted_texts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze font characteristics for authenticity"""

        # This is a simplified analysis - real implementation would use more sophisticated font analysis
        total_confidence = sum(item.get("confidence", 0) for item in extracted_texts)
        avg_confidence = total_confidence / len(extracted_texts) if extracted_texts else 0

        # High OCR confidence suggests good font quality
        score = min(avg_confidence / 100, 1.0)

        return {
            "score": score,
            "average_ocr_confidence": avg_confidence,
            "assessment": "good" if score > 0.7 else "poor" if score < 0.4 else "moderate"
        }

    def _check_spacing_uniformity(self, extracted_texts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Check uniformity of character spacing"""

        # Simplified spacing analysis
        # Real implementation would analyze actual character positions

        texts_with_multiple_words = [item for item in extracted_texts if item.get("word_count", 0) > 1]

        if not texts_with_multiple_words:
            return {"score": 0.5, "assessment": "insufficient_data"}

        # Assume uniform spacing if we have multiple words with reasonable confidence
        avg_confidence = sum(item.get("confidence", 0) for item in texts_with_multiple_words) / len(texts_with_multiple_words)

        score = min(avg_confidence / 100, 1.0)

        return {
            "score": score,
            "assessment": "uniform" if score > 0.6 else "irregular"
        }

    def _assess_character_clarity(self, extracted_texts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Assess clarity of individual characters"""

        if not extracted_texts:
            return {"score": 0, "assessment": "no_text_found"}

        # Use OCR confidence as proxy for character clarity
        confidences = [item.get("confidence", 0) for item in extracted_texts]
        avg_confidence = sum(confidences) / len(confidences)

        score = min(avg_confidence / 100, 1.0)

        return {
            "score": score,
            "average_confidence": avg_confidence,
            "assessment": "clear" if score > 0.7 else "unclear" if score < 0.4 else "moderate"
        }

    def _detect_suspicious_patterns(self, text: str) -> List[str]:
        """Detect patterns that might indicate counterfeit markings"""

        suspicious_patterns = []

        # Check for repeated characters (might indicate poor printing)
        if re.search(r'(.)\1{3,}', text):
            suspicious_patterns.append("Repeated characters found")

        # Check for unusual character combinations
        if re.search(r'[^\w\s]', text):  # Non-alphanumeric characters in IC markings
            suspicious_patterns.append("Unusual symbols in marking")

        # Check for very short text fragments
        words = text.split()
        if len(words) > 0 and sum(len(word) for word in words) / len(words) < 3:
            suspicious_patterns.append("Abnormally short text fragments")

        return suspicious_patterns
