"""
Main IC verification service - orchestrates all verification components
"""
import asyncio
import cv2
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import io

from config.settings import settings
from services.image_processing import ImageProcessingService
from services.ocr_service import OCRService
from services.logo_detection import LogoDetectionService
from services.font_analysis import FontAnalysisService
from services.datasheet_service import DatasheetService
from models.database import IC, Manufacturer

logger = logging.getLogger(__name__)


class ICVerificationService:
    """Main service for IC verification orchestrating all components"""

    def __init__(self):
        self.image_service = ImageProcessingService()
        self.ocr_service = OCRService()
        self.logo_service = LogoDetectionService()
        self.font_service = FontAnalysisService()
        self.datasheet_service = DatasheetService()

        # Thread pool for CPU-intensive operations
        self.executor = ThreadPoolExecutor(max_workers=4)

    async def verify_ic_from_image(
        self,
        image_content: bytes,
        filename: str = None,
        part_number: Optional[str] = None,
        manufacturer: Optional[str] = None,
        thorough_check: bool = True
    ) -> Dict[str, Any]:
        """Verify IC authenticity from image"""

        try:
            start_time = datetime.utcnow()

            # Step 1: Process image
            logger.info("Step 1: Processing image")
            processed_result = await self.image_service.process_image(
                image_content, filename or "ic_image.jpg", preprocess=True, enhance_contrast=True
            )

            if not processed_result.get("processed_path"):
                return {
                    "error": "Image processing failed",
                    "is_genuine": False,
                    "confidence": 0
                }

            # Load processed image
            processed_image = cv2.imread(processed_result["processed_path"], cv2.IMREAD_GRAYSCALE)

            # Step 2: Extract text markings
            logger.info("Step 2: Extracting text markings")
            text_regions = await self._extract_text_regions(processed_image)

            # Step 3: OCR analysis
            logger.info("Step 3: Performing OCR analysis")
            ocr_result = await self.ocr_service.extract_text(
                processed_image, text_regions, preprocess=False
            )

            # Step 4: Identify part number and manufacturer
            logger.info("Step 4: Identifying part number and manufacturer")
            identification_result = self._identify_ic_from_ocr(ocr_result, part_number, manufacturer)

            # Step 5: Logo detection
            logger.info("Step 5: Detecting manufacturer logo")
            logo_result = await self.logo_service.detect_logo(
                processed_image, identification_result.get("manufacturer")
            )

            # Step 6: Font analysis
            logger.info("Step 6: Analyzing font characteristics")
            font_result = await self.font_service.analyze_font(
                processed_image, text_regions, identification_result.get("manufacturer")
            )

            # Step 7: Counterfeit detection
            logger.info("Step 7: Detecting counterfeit indicators")
            counterfeit_result = await self.font_service.detect_counterfeit_indicators(
                processed_image, text_regions
            )

            # Step 8: Datasheet verification (if part number known)
            datasheet_result = {}
            if identification_result.get("part_number") and thorough_check:
                logger.info("Step 8: Verifying against datasheet")
                datasheet_result = await self._verify_against_datasheet(
                    identification_result["part_number"]
                )

            # Step 9: Final authenticity assessment
            logger.info("Step 9: Assessing overall authenticity")
            final_result = self._assess_overall_authenticity(
                identification_result,
                ocr_result,
                logo_result,
                font_result,
                counterfeit_result,
                datasheet_result
            )

            processing_time = (datetime.utcnow() - start_time).total_seconds()

            # Compile comprehensive result
            result = {
                "detected_part_number": identification_result.get("part_number"),
                "detected_manufacturer": identification_result.get("manufacturer"),
                "detected_text": ocr_result.get("extracted_text", []),
                "confidence_scores": {
                    "ocr": ocr_result.get("analysis", {}).get("classification_confidence", {}).get("total_classified_elements", 0) / 10,
                    "logo": logo_result.get("confidence", 0),
                    "font": font_result.get("authenticity_score", 0)
                },
                "logo_match_score": logo_result.get("confidence", 0),
                "font_similarity_score": font_result.get("font_similarity_score", 0),
                "marking_accuracy_score": self._calculate_marking_accuracy(ocr_result),
                "overall_confidence": final_result["overall_confidence"],
                "is_genuine": final_result["is_genuine"],
                "authenticity_reasons": final_result["reasons"],
                "analysis_results": {
                    "identification": identification_result,
                    "ocr_analysis": ocr_result.get("analysis", {}),
                    "logo_detection": logo_result,
                    "font_analysis": font_result,
                    "counterfeit_indicators": counterfeit_result,
                    "datasheet_verification": datasheet_result
                },
                "processing_time_seconds": processing_time
            }

            return result

        except Exception as e:
            logger.error(f"Error in IC verification: {e}")
            return {
                "error": str(e),
                "is_genuine": False,
                "confidence": 0,
                "processing_time_seconds": (datetime.utcnow() - datetime.utcnow()).total_seconds()
            }

    async def verify_ic_from_path(
        self,
        image_path: str,
        part_number: Optional[str] = None,
        manufacturer: Optional[str] = None,
        thorough_check: bool = True
    ) -> Dict[str, Any]:
        """Verify IC from image path"""

        try:
            with open(image_path, "rb") as f:
                image_content = f.read()

            filename = os.path.basename(image_path)
            return await self.verify_ic_from_image(
                image_content, filename, part_number, manufacturer, thorough_check
            )

        except Exception as e:
            logger.error(f"Error loading image from path {image_path}: {e}")
            return {
                "error": f"Could not load image: {str(e)}",
                "is_genuine": False,
                "confidence": 0
            }

    async def _extract_text_regions(self, image: np.ndarray) -> List[Dict[str, Any]]:
        """Extract text regions from image"""

        # Use image processing service to find text regions
        analysis = await self.image_service.analyze_image("temp", "text_regions")

        # Since we don't have the actual image ID, create mock regions
        # In real implementation, this would be integrated properly

        # Simple text region detection
        text_regions = []

        # Apply thresholding to find potential text areas
        _, thresh = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # Find contours
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for contour in contours:
            area = cv2.contourArea(contour)
            if 500 < area < 10000:  # Reasonable text region size
                x, y, w, h = cv2.boundingRect(contour)
                aspect_ratio = w / h if h > 0 else 0

                # Text-like aspect ratio
                if 2 < aspect_ratio < 20:
                    text_regions.append({
                        "bbox": [x, y, w, h],
                        "area": area,
                        "aspect_ratio": aspect_ratio,
                        "confidence": min(1.0, area / 5000)
                    })

        # Sort by confidence and return top regions
        text_regions.sort(key=lambda x: x["confidence"], reverse=True)
        return text_regions[:10]

    def _identify_ic_from_ocr(
        self,
        ocr_result: Dict[str, Any],
        provided_part_number: Optional[str] = None,
        provided_manufacturer: Optional[str] = None
    ) -> Dict[str, Any]:
        """Identify IC from OCR results"""

        analysis = ocr_result.get("analysis", {})

        # Use provided values if available
        part_number = provided_part_number
        manufacturer = provided_manufacturer

        # Extract from OCR if not provided
        if not part_number:
            potential_parts = analysis.get("potential_part_numbers", [])
            if potential_parts:
                # Take the highest confidence part number
                best_part = max(potential_parts, key=lambda x: x["confidence"])
                part_number = best_part["text"]

        if not manufacturer:
            potential_manufacturers = analysis.get("potential_manufacturer_codes", [])
            if potential_manufacturers:
                # Take the highest confidence manufacturer
                best_manufacturer = max(potential_manufacturers, key=lambda x: x["confidence"])
                manufacturer_code = best_manufacturer["text"]

                # Map code to full manufacturer name
                code_to_manufacturer = {
                    "STM": "STMicroelectronics",
                    "TI": "Texas Instruments",
                    "NXP": "NXP",
                    "MAX": "Analog Devices",
                    "INF": "Infineon",
                    "MICROCHIP": "Microchip",
                    "ONSEMI": "ON Semiconductor"
                }

                manufacturer = code_to_manufacturer.get(manufacturer_code.upper())

        return {
            "part_number": part_number,
            "manufacturer": manufacturer,
            "confidence": self._calculate_identification_confidence(analysis)
        }

    def _calculate_identification_confidence(self, analysis: Dict[str, Any]) -> float:
        """Calculate confidence in IC identification"""

        confidence = 0

        # Part number confidence
        if analysis.get("potential_part_numbers"):
            part_conf = max([p["confidence"] for p in analysis["potential_part_numbers"]])
            confidence += part_conf * 0.5

        # Manufacturer confidence
        if analysis.get("potential_manufacturer_codes"):
            manu_conf = max([m["confidence"] for m in analysis["potential_manufacturer_codes"]])
            confidence += manu_conf * 0.3

        # Overall classification confidence
        class_conf = analysis.get("classification_confidence", {})
        if class_conf.get("has_part_number"):
            confidence += 0.2

        return min(confidence, 1.0)

    def _calculate_marking_accuracy(self, ocr_result: Dict[str, Any]) -> float:
        """Calculate accuracy of markings"""

        analysis = ocr_result.get("analysis", {})

        # Base accuracy on OCR confidence and classification
        ocr_confidence = 0
        extracted_texts = ocr_result.get("extracted_text", [])

        if extracted_texts:
            avg_confidence = sum([text.get("confidence", 0) for text in extracted_texts]) / len(extracted_texts)
            ocr_confidence = avg_confidence / 100  # Convert to 0-1 scale

        # Classification bonus
        class_conf = analysis.get("classification_confidence", {})
        classification_bonus = sum([
            0.2 if class_conf.get("has_part_number") else 0,
            0.1 if class_conf.get("has_manufacturer_code") else 0,
            0.1 if class_conf.get("has_date_code") else 0,
            0.1 if class_conf.get("has_lot_code") else 0
        ])

        return min(ocr_confidence + classification_bonus, 1.0)

    async def _verify_against_datasheet(self, part_number: str) -> Dict[str, Any]:
        """Verify IC against datasheet specifications"""

        try:
            # Fetch datasheet
            datasheet_result = await self.datasheet_service.fetch_datasheet(part_number)

            if not datasheet_result.get("success"):
                return {"error": "Could not fetch datasheet"}

            # Parse datasheet
            with open(datasheet_result["local_path"], "rb") as f:
                content = f.read()

            parsed_specs = await self.datasheet_service.parse_datasheet(content)

            return {
                "datasheet_found": True,
                "specifications": parsed_specs.get("extracted_specs", {}),
                "parsing_confidence": parsed_specs.get("confidence", 0)
            }

        except Exception as e:
            logger.error(f"Error verifying against datasheet: {e}")
            return {"error": str(e)}

    def _assess_overall_authenticity(
        self,
        identification: Dict[str, Any],
        ocr_result: Dict[str, Any],
        logo_result: Dict[str, Any],
        font_result: Dict[str, Any],
        counterfeit_result: Dict[str, Any],
        datasheet_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Assess overall IC authenticity"""

        reasons = []
        confidence_scores = []

        # Logo verification (40% weight)
        logo_confidence = logo_result.get("confidence", 0)
        if logo_confidence > settings.verification_thresholds["logo_match"]:
            reasons.append("Logo matches genuine manufacturer logo")
            confidence_scores.append(logo_confidence * 0.4)
        else:
            reasons.append("Logo verification failed")
            confidence_scores.append(0)

        # Font analysis (30% weight)
        font_confidence = font_result.get("authenticity_score", 0)
        if font_confidence > settings.verification_thresholds["font_similarity"]:
            reasons.append("Font characteristics match genuine IC markings")
            confidence_scores.append(font_confidence * 0.3)
        else:
            reasons.append("Font analysis indicates potential counterfeit")
            confidence_scores.append(font_confidence * 0.3)

        # Marking accuracy (20% weight)
        marking_confidence = self._calculate_marking_accuracy(ocr_result)
        if marking_confidence > settings.verification_thresholds["marking_accuracy"]:
            reasons.append("Marking accuracy meets standards")
            confidence_scores.append(marking_confidence * 0.2)
        else:
            reasons.append("Marking accuracy below standard")
            confidence_scores.append(marking_confidence * 0.2)

        # Counterfeit indicators (10% weight)
        counterfeit_probability = counterfeit_result.get("counterfeit_probability", 0)
        authenticity_from_counterfeit = 1 - counterfeit_probability
        if authenticity_from_counterfeit > 0.7:
            reasons.append("No significant counterfeit indicators detected")
        else:
            reasons.append("Counterfeit indicators detected")
        confidence_scores.append(authenticity_from_counterfeit * 0.1)

        # Overall confidence
        overall_confidence = sum(confidence_scores) if confidence_scores else 0

        # Final genuine/fake determination
        is_genuine = overall_confidence > settings.verification_thresholds["overall_confidence"]

        if is_genuine:
            reasons.append(f"Overall confidence ({overall_confidence:.2f}) exceeds threshold")
        else:
            reasons.append(f"Overall confidence ({overall_confidence:.2f}) below threshold")

        # Additional checks
        if datasheet_result and not datasheet_result.get("error"):
            reasons.append("Datasheet verification successful")
            overall_confidence = min(overall_confidence + 0.1, 1.0)

        return {
            "is_genuine": is_genuine,
            "overall_confidence": overall_confidence,
            "reasons": reasons,
            "component_scores": {
                "logo": logo_confidence,
                "font": font_confidence,
                "marking": marking_confidence,
                "counterfeit_check": authenticity_from_counterfeit
            }
        }

    async def batch_verify_ics(
        self,
        images: List[Dict[str, Any]],
        thorough_check: bool = False
    ) -> List[Dict[str, Any]]:
        """Batch verify multiple ICs"""

        results = []

        # Process images concurrently
        tasks = []
        for image_data in images:
            task = self.verify_ic_from_image(
                image_data["content"],
                image_data.get("filename", "batch_image.jpg"),
                image_data.get("part_number"),
                image_data.get("manufacturer"),
                thorough_check
            )
            tasks.append(task)

        # Execute all tasks
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)

        for i, result in enumerate(batch_results):
            if isinstance(result, Exception):
                results.append({
                    "filename": images[i].get("filename", f"image_{i}"),
                    "error": str(result),
                    "is_genuine": False,
                    "confidence": 0
                })
            else:
                results.append(result)

        return results

    async def get_verification_statistics(self) -> Dict[str, Any]:
        """Get verification statistics"""

        # This would query the database for statistics
        # Placeholder implementation
        return {
            "total_verifications": 0,
            "genuine_detected": 0,
            "counterfeit_detected": 0,
            "average_confidence": 0,
            "top_manufacturers": [],
            "recent_verifications": []
        }
