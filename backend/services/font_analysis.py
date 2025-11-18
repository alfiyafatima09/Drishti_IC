"""
Font analysis service for IC authenticity verification
"""
import cv2
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
import logging
from datetime import datetime
import os
import pickle

from config.settings import settings

logger = logging.getLogger(__name__)


class FontAnalysisService:
    """Service for analyzing fonts in IC markings for authenticity verification"""

    def __init__(self):
        self.reference_fonts = {}  
        self._load_reference_fonts()

    def _load_reference_fonts(self):
        """Load reference font samples for supported manufacturers"""

        fonts_dir = os.path.join(os.getcwd(), "data", "fonts")
        os.makedirs(fonts_dir, exist_ok=True)

        # This would load reference font images for each manufacturer
        # For now, we'll initialize with placeholder data
        for manufacturer in settings.supported_manufacturers.keys():
            font_samples_path = os.path.join(fonts_dir, f"{manufacturer.lower()}_fonts.pkl")
            if os.path.exists(font_samples_path):
                try:
                    with open(font_samples_path, 'rb') as f:
                        self.reference_fonts[manufacturer] = pickle.load(f)
                    logger.info(f"Loaded reference fonts for {manufacturer}")
                except Exception as e:
                    logger.error(f"Error loading fonts for {manufacturer}: {e}")

    async def analyze_font(
        self,
        image: np.ndarray,
        text_regions: List[Dict[str, Any]],
        expected_manufacturer: Optional[str] = None
    ) -> Dict[str, Any]:
        """Analyze font characteristics in IC markings"""

        try:
            start_time = datetime.utcnow()

            if not text_regions:
                return {
                    "font_similarity_score": 0,
                    "confidence": 0,
                    "reason": "No text regions provided",
                    "processing_time_seconds": (datetime.utcnow() - start_time).total_seconds()
                }

            # Extract individual characters from text regions
            characters = self._extract_characters(image, text_regions)

            if not characters:
                return {
                    "font_similarity_score": 0,
                    "confidence": 0,
                    "reason": "No characters extracted",
                    "processing_time_seconds": (datetime.utcnow() - start_time).total_seconds()
                }

            # Analyze font characteristics
            font_features = self._analyze_font_features(characters)

            # Compare with reference fonts
            similarity_scores = []

            manufacturers_to_check = [expected_manufacturer] if expected_manufacturer else list(self.reference_fonts.keys())

            for manufacturer in manufacturers_to_check:
                if manufacturer in self.reference_fonts:
                    score = self._compare_with_reference_font(characters, manufacturer)
                    similarity_scores.append({
                        "manufacturer": manufacturer,
                        "similarity_score": score
                    })

            # Sort by similarity
            similarity_scores.sort(key=lambda x: x["similarity_score"], reverse=True)

            best_match = similarity_scores[0] if similarity_scores else None

            # Calculate overall authenticity score
            authenticity_score = self._calculate_authenticity_score(font_features, best_match)

            processing_time = (datetime.utcnow() - start_time).total_seconds()

            return {
                "font_similarity_score": best_match["similarity_score"] if best_match else 0,
                "best_match_manufacturer": best_match["manufacturer"] if best_match else None,
                "all_similarity_scores": similarity_scores,
                "font_features": font_features,
                "authenticity_score": authenticity_score,
                "character_count": len(characters),
                "processing_time_seconds": processing_time
            }

        except Exception as e:
            logger.error(f"Error in font analysis: {e}")
            return {
                "font_similarity_score": 0,
                "confidence": 0,
                "error": str(e)
            }

    def _extract_characters(
        self,
        image: np.ndarray,
        text_regions: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Extract individual characters from text regions"""

        characters = []

        for region in text_regions:
            bbox = region.get("bbox")
            if not bbox:
                continue

            x, y, w, h = bbox

            # Extract region of interest
            roi = image[y:y+h, x:x+w]

            if roi.size == 0:
                continue

            # Convert to grayscale if needed
            if len(roi.shape) == 3:
                roi_gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            else:
                roi_gray = roi

            # Apply thresholding to get binary image
            _, thresh = cv2.threshold(roi_gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

            # Find contours (potential characters)
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            for contour in contours:
                char_area = cv2.contourArea(contour)
                if 50 < char_area < 5000:  # Reasonable character size
                    char_x, char_y, char_w, char_h = cv2.boundingRect(contour)

                    # Extract character image
                    char_img = thresh[char_y:char_y+char_h, char_x:char_x+char_w]

                    if char_img.size > 0 and char_img.shape[0] > 5 and char_img.shape[1] > 3:
                        characters.append({
                            "image": char_img,
                            "bbox": [char_x + x, char_y + y, char_w, char_h],  # Global coordinates
                            "area": char_area,
                            "aspect_ratio": char_w / char_h if char_h > 0 else 0,
                            "region_id": region.get("id", "unknown")
                        })

        return characters

    def _analyze_font_features(self, characters: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze font characteristics from extracted characters"""

        if not characters:
            return {"error": "No characters to analyze"}

        # Calculate various font metrics
        aspect_ratios = [char["aspect_ratio"] for char in characters]
        areas = [char["area"] for char in characters]

        # Stroke width analysis
        stroke_widths = []
        for char in characters:
            img = char["image"]
            if img.size > 0:
                # Simple stroke width calculation
                contours, _ = cv2.findContours(img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                if contours:
                    # Approximate stroke width as average distance from contour
                    cnt = contours[0]
                    area = cv2.contourArea(cnt)
                    perimeter = cv2.arcLength(cnt, True)
                    if perimeter > 0:
                        stroke_width = area / perimeter
                        stroke_widths.append(stroke_width)

        # Spacing analysis (simplified)
        spacing_uniformity = self._analyze_spacing_uniformity(characters)

        # Serif analysis (simplified)
        serif_characteristics = self._analyze_serif_characteristics(characters)

        return {
            "average_aspect_ratio": np.mean(aspect_ratios) if aspect_ratios else 0,
            "aspect_ratio_std": np.std(aspect_ratios) if aspect_ratios else 0,
            "average_area": np.mean(areas) if areas else 0,
            "area_std": np.std(areas) if areas else 0,
            "average_stroke_width": np.mean(stroke_widths) if stroke_widths else 0,
            "stroke_width_std": np.std(stroke_widths) if stroke_widths else 0,
            "spacing_uniformity": spacing_uniformity,
            "serif_characteristics": serif_characteristics,
            "character_consistency": self._assess_character_consistency(characters)
        }

    def _analyze_spacing_uniformity(self, characters: List[Dict[str, Any]]) -> float:
        """Analyze uniformity of character spacing"""

        if len(characters) < 2:
            return 0.5  # Neutral score

        # Sort characters by x-coordinate
        sorted_chars = sorted(characters, key=lambda c: c["bbox"][0])

        # Calculate spacing between consecutive characters
        spacings = []
        for i in range(len(sorted_chars) - 1):
            curr_char = sorted_chars[i]
            next_char = sorted_chars[i + 1]

            # Check if they're on the same line (similar y-coordinate)
            curr_center_y = curr_char["bbox"][1] + curr_char["bbox"][3] / 2
            next_center_y = next_char["bbox"][1] + next_char["bbox"][3] / 2

            if abs(curr_center_y - next_center_y) < curr_char["bbox"][3] * 0.5:
                # Same line, calculate spacing
                spacing = next_char["bbox"][0] - (curr_char["bbox"][0] + curr_char["bbox"][2])
                if spacing > 0:  # Positive spacing
                    spacings.append(spacing)

        if not spacings:
            return 0.5

        # Calculate uniformity (1 - coefficient of variation)
        spacing_std = np.std(spacings)
        spacing_mean = np.mean(spacings)

        if spacing_mean > 0:
            uniformity = 1 - (spacing_std / spacing_mean)
            return max(0, min(1, uniformity))
        else:
            return 0.5

    def _analyze_serif_characteristics(self, characters: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze serif characteristics (simplified)"""

        serif_indicators = []

        for char in characters:
            img = char["image"]

            # Look for serif-like features at character edges
            height, width = img.shape

            # Check top and bottom edges for horizontal lines (serifs)
            top_edge = img[0, :]
            bottom_edge = img[-1, :]

            top_serif_score = np.sum(top_edge > 127) / width
            bottom_serif_score = np.sum(bottom_edge > 127) / width

            # Check left and right edges for vertical serifs
            left_edge = img[:, 0]
            right_edge = img[:, -1]

            left_serif_score = np.sum(left_edge > 127) / height
            right_serif_score = np.sum(right_edge > 127) / height

            serif_score = (top_serif_score + bottom_serif_score + left_serif_score + right_serif_score) / 4

            serif_indicators.append(serif_score)

        return {
            "average_serif_score": np.mean(serif_indicators) if serif_indicators else 0,
            "serif_consistency": 1 - np.std(serif_indicators) if serif_indicators else 0
        }

    def _assess_character_consistency(self, characters: List[Dict[str, Any]]) -> float:
        """Assess overall consistency of characters"""

        if len(characters) < 2:
            return 0.5

        # Calculate various consistency metrics
        aspect_ratios = [char["aspect_ratio"] for char in characters]
        areas = [char["area"] for char in characters]

        aspect_consistency = 1 - (np.std(aspect_ratios) / np.mean(aspect_ratios)) if aspect_ratios else 0
        area_consistency = 1 - (np.std(areas) / np.mean(areas)) if areas else 0

        # Ensure values are between 0 and 1
        aspect_consistency = max(0, min(1, aspect_consistency))
        area_consistency = max(0, min(1, area_consistency))

        overall_consistency = (aspect_consistency + area_consistency) / 2

        return overall_consistency

    def _compare_with_reference_font(
        self,
        characters: List[Dict[str, Any]],
        manufacturer: str
    ) -> float:
        """Compare extracted characters with reference font"""

        if manufacturer not in self.reference_fonts:
            return 0

        reference_data = self.reference_fonts[manufacturer]

        # This is a simplified comparison - real implementation would use more sophisticated methods
        similarity_scores = []

        for char in characters:
            char_img = char["image"]

            # Resize character to standard size for comparison
            resized_char = cv2.resize(char_img, (50, 50))

            # Compare with reference character samples
            # This is placeholder logic - real implementation would compare against
            # known good samples of each character
            char_similarity = self._compute_character_similarity(resized_char, reference_data)
            similarity_scores.append(char_similarity)

        if similarity_scores:
            return np.mean(similarity_scores)
        else:
            return 0

    def _compute_character_similarity(
        self,
        character_img: np.ndarray,
        reference_data: Dict[str, Any]
    ) -> float:
        """Compute similarity between character and reference"""

        # Placeholder similarity computation
        # Real implementation would use trained models or comprehensive reference comparison

        # Simple metrics
        pixel_density = np.sum(character_img > 127) / character_img.size
        edge_density = np.sum(cv2.Canny(character_img, 50, 150) > 0) / character_img.size

        # Combine metrics (this is arbitrary and should be replaced with real training)
        similarity = (pixel_density * 0.6) + (edge_density * 0.4)

        return min(similarity, 1.0)

    def _calculate_authenticity_score(
        self,
        font_features: Dict[str, Any],
        best_match: Optional[Dict[str, Any]]
    ) -> float:
        """Calculate overall authenticity score based on font analysis"""

        if not best_match:
            return 0

        base_similarity = best_match["similarity_score"]

        # Adjust based on font features
        consistency_bonus = font_features.get("character_consistency", 0) * 0.2
        spacing_bonus = font_features.get("spacing_uniformity", 0) * 0.1
        serif_bonus = font_features.get("serif_characteristics", {}).get("serif_consistency", 0) * 0.1

        # Penalize for high variability in stroke width
        stroke_penalty = (1 - font_features.get("stroke_width_std", 0) / 5) * 0.1

        authenticity_score = base_similarity + consistency_bonus + spacing_bonus + serif_bonus + stroke_penalty

        return max(0, min(1, authenticity_score))

    async def detect_counterfeit_indicators(
        self,
        image: np.ndarray,
        text_regions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Detect specific indicators of counterfeit markings"""

        counterfeit_indicators = {
            "slanted_characters": self._detect_slanted_characters(image, text_regions),
            "inconsistent_stroke_width": self._detect_inconsistent_stroke_width(image, text_regions),
            "character_deformation": self._detect_character_deformation(image, text_regions),
            "poor_alignment": self._detect_poor_alignment(image, text_regions),
            "erasable_ink_indicators": self._detect_erasable_ink_indicators(image, text_regions)
        }

        # Calculate overall counterfeit probability
        indicator_weights = {
            "slanted_characters": 0.25,
            "inconsistent_stroke_width": 0.2,
            "character_deformation": 0.25,
            "poor_alignment": 0.15,
            "erasable_ink_indicators": 0.15
        }

        counterfeit_probability = 0
        total_weight = 0

        for indicator, weight in indicator_weights.items():
            if indicator in counterfeit_indicators:
                score = counterfeit_indicators[indicator].get("score", 0)
                counterfeit_probability += score * weight
                total_weight += weight

        if total_weight > 0:
            counterfeit_probability /= total_weight

        return {
            "counterfeit_indicators": counterfeit_indicators,
            "counterfeit_probability": counterfeit_probability,
            "authenticity_confidence": 1 - counterfeit_probability
        }

    def _detect_slanted_characters(
        self,
        image: np.ndarray,
        text_regions: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """Detect slanted characters (common counterfeit indicator)"""

        characters = self._extract_characters(image, text_regions)

        slant_scores = []

        for char in characters:
            img = char["image"]

            # Calculate vertical projection
            projection = np.sum(img, axis=1)

            # Find the peak (main character body)
            peak_idx = np.argmax(projection)

            # Check slant by comparing left and right sides
            left_half = img[:, :img.shape[1]//2]
            right_half = img[:, img.shape[1]//2:]

            left_density = np.sum(left_half) / left_half.size
            right_density = np.sum(right_half) / right_half.size

            # Significant imbalance indicates slant
            slant_score = abs(left_density - right_density) / max(left_density, right_density, 1)

            slant_scores.append(slant_score)

        if slant_scores:
            avg_slant = np.mean(slant_scores)
            # Higher values indicate more slant
            return {
                "score": min(avg_slant * 2, 1.0),  # Scale for better sensitivity
                "average_slant": avg_slant,
                "assessment": "slanted" if avg_slant > 0.3 else "straight"
            }
        else:
            return {"score": 0, "average_slant": 0, "assessment": "unknown"}

    def _detect_inconsistent_stroke_width(
        self,
        image: np.ndarray,
        text_regions: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """Detect inconsistent stroke width"""

        characters = self._extract_characters(image, text_regions)

        stroke_widths = []

        for char in characters:
            img = char["image"]

            # Simple stroke width calculation
            contours, _ = cv2.findContours(img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if contours:
                cnt = contours[0]
                area = cv2.contourArea(cnt)
                perimeter = cv2.arcLength(cnt, True)
                if perimeter > 0:
                    stroke_width = area / perimeter
                    stroke_widths.append(stroke_width)

        if len(stroke_widths) > 1:
            stroke_std = np.std(stroke_widths)
            stroke_mean = np.mean(stroke_widths)

            if stroke_mean > 0:
                consistency_score = stroke_std / stroke_mean
                return {
                    "score": min(consistency_score, 1.0),
                    "stroke_width_std": stroke_std,
                    "stroke_width_mean": stroke_mean,
                    "assessment": "inconsistent" if consistency_score > 0.3 else "consistent"
                }

        return {"score": 0, "assessment": "insufficient_data"}

    def _detect_character_deformation(
        self,
        image: np.ndarray,
        text_regions: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """Detect character deformation"""

        characters = self._extract_characters(image, text_regions)

        deformation_scores = []

        for char in characters:
            img = char["image"]

            # Check for irregular shapes using contour analysis
            contours, _ = cv2.findContours(img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if contours:
                cnt = contours[0]

                # Calculate solidity (area / convex hull area)
                area = cv2.contourArea(cnt)
                hull = cv2.convexHull(cnt)
                hull_area = cv2.contourArea(hull)

                if hull_area > 0:
                    solidity = area / hull_area
                    # Lower solidity indicates more deformation
                    deformation_score = 1 - solidity
                    deformation_scores.append(deformation_score)

        if deformation_scores:
            avg_deformation = np.mean(deformation_scores)
            return {
                "score": avg_deformation,
                "average_deformation": avg_deformation,
                "assessment": "deformed" if avg_deformation > 0.2 else "regular"
            }

        return {"score": 0, "assessment": "unknown"}

    def _detect_poor_alignment(
        self,
        image: np.ndarray,
        text_regions: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """Detect poor character alignment"""

        characters = self._extract_characters(image, text_regions)

        if len(characters) < 2:
            return {"score": 0, "assessment": "insufficient_characters"}

        # Sort by y-coordinate
        sorted_chars = sorted(characters, key=lambda c: c["bbox"][1])

        # Group into lines
        lines = []
        current_line = [sorted_chars[0]]

        for char in sorted_chars[1:]:
            last_char = current_line[-1]

            # Check if on same line
            if abs(char["bbox"][1] - last_char["bbox"][1]) < last_char["bbox"][3] * 0.5:
                current_line.append(char)
            else:
                lines.append(current_line)
                current_line = [char]

        if current_line:
            lines.append(current_line)

        # Calculate alignment for each line
        alignment_scores = []

        for line in lines:
            if len(line) > 1:
                # Calculate baseline alignment
                baselines = [char["bbox"][1] + char["bbox"][3] for char in line]
                baseline_std = np.std(baselines)

                # Normalize by character height
                avg_height = np.mean([char["bbox"][3] for char in line])
                if avg_height > 0:
                    normalized_std = baseline_std / avg_height
                    alignment_scores.append(normalized_std)

        if alignment_scores:
            avg_alignment_score = np.mean(alignment_scores)
            return {
                "score": min(avg_alignment_score, 1.0),
                "average_alignment_error": avg_alignment_score,
                "assessment": "poor" if avg_alignment_score > 0.2 else "good"
            }

        return {"score": 0, "assessment": "unknown"}

    def _detect_erasable_ink_indicators(
        self,
        image: np.ndarray,
        text_regions: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """Detect indicators of erasable ink (acetone test simulation)"""

        # This is a simplified simulation - real implementation would need
        # specific image processing for erasable ink detection

        # Check for ink spread or bleeding
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image

        # Apply blur and compare with original
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        diff = cv2.absdiff(gray.astype(float), blurred.astype(float))

        # High difference might indicate ink spreading
        ink_spread_score = np.mean(diff) / 255

        return {
            "score": ink_spread_score,
            "ink_spread_indicator": ink_spread_score,
            "assessment": "potential_erasable_ink" if ink_spread_score > 0.3 else "normal_ink"
        }
