"""
Logo detection service using SIFT and Context-Dependent Similarity (CDS) kernel
"""
import cv2
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
import os
import logging
from datetime import datetime
import pickle

from config.settings import settings

logger = logging.getLogger(__name__)


class LogoDetectionService:
    """Service for detecting manufacturer logos using SIFT and CDS kernel"""

    def __init__(self):
        self.sift = cv2.SIFT_create(nfeatures=settings.sift_nfeatures)
        self.reference_logos = {}  # Cache for loaded reference logos
        self._load_reference_logos()

    def _load_reference_logos(self):
        """Load reference logos for supported manufacturers"""

        logo_dir = os.path.join(os.getcwd(), "data", "logos")
        os.makedirs(logo_dir, exist_ok=True)

        for manufacturer, data in settings.supported_manufacturers.items():
            logo_path = os.path.join(logo_dir, f"{manufacturer.lower()}_logo.jpg")
            if os.path.exists(logo_path):
                try:
                    logo_img = cv2.imread(logo_path, cv2.IMREAD_GRAYSCALE)
                    if logo_img is not None:
                        keypoints, descriptors = self._extract_sift_features(logo_img)
                        self.reference_logos[manufacturer] = {
                            "image": logo_img,
                            "keypoints": keypoints,
                            "descriptors": descriptors,
                            "path": logo_path
                        }
                        logger.info(f"Loaded reference logo for {manufacturer}")
                except Exception as e:
                    logger.error(f"Error loading logo for {manufacturer}: {e}")

    def _extract_sift_features(self, image: np.ndarray) -> Tuple[List[cv2.KeyPoint], np.ndarray]:
        """Extract SIFT keypoints and descriptors from image"""

        keypoints, descriptors = self.sift.detectAndCompute(image, None)

        # Filter weak keypoints
        if descriptors is not None:
            # Keep only keypoints with good response
            good_indices = [i for i, kp in enumerate(keypoints) if kp.response > 0.01]
            keypoints = [keypoints[i] for i in good_indices]
            descriptors = descriptors[good_indices]

        return keypoints, descriptors

    async def detect_logo(
        self,
        image: np.ndarray,
        manufacturer: Optional[str] = None,
        use_cds: bool = True
    ) -> Dict[str, Any]:
        """Detect manufacturer logo in image"""

        try:
            start_time = datetime.utcnow()

            # Extract SIFT features from test image
            test_keypoints, test_descriptors = self._extract_sift_features(image)

            if test_descriptors is None or len(test_descriptors) < 4:
                return {
                    "detected": False,
                    "confidence": 0,
                    "reason": "Insufficient features in test image",
                    "processing_time_seconds": (datetime.utcnow() - start_time).total_seconds()
                }

            results = []

            # Compare against reference logos
            manufacturers_to_check = [manufacturer] if manufacturer else list(self.reference_logos.keys())

            for manu in manufacturers_to_check:
                if manu not in self.reference_logos:
                    continue

                ref_data = self.reference_logos[manu]

                if ref_data["descriptors"] is None or len(ref_data["descriptors"]) < 4:
                    continue

                # Match features
                if use_cds:
                    match_result = self._cds_similarity_matching(
                        test_keypoints, test_descriptors,
                        ref_data["keypoints"], ref_data["descriptors"],
                        image, ref_data["image"]
                    )
                else:
                    match_result = self._standard_feature_matching(
                        test_descriptors, ref_data["descriptors"]
                    )

                match_result["manufacturer"] = manu
                results.append(match_result)

            # Sort by confidence
            results.sort(key=lambda x: x["confidence"], reverse=True)

            best_match = results[0] if results else None

            processing_time = (datetime.utcnow() - start_time).total_seconds()

            if best_match and best_match["confidence"] > settings.logo_match_threshold:
                return {
                    "detected": True,
                    "manufacturer": best_match["manufacturer"],
                    "confidence": best_match["confidence"],
                    "match_details": best_match,
                    "all_matches": results[:3],  # Top 3 matches
                    "processing_time_seconds": processing_time
                }
            else:
                return {
                    "detected": False,
                    "confidence": best_match["confidence"] if best_match else 0,
                    "reason": "No logo match above threshold",
                    "all_matches": results[:3] if results else [],
                    "processing_time_seconds": processing_time
                }

        except Exception as e:
            logger.error(f"Error in logo detection: {e}")
            return {
                "detected": False,
                "confidence": 0,
                "error": str(e)
            }

    def _standard_feature_matching(
        self,
        test_descriptors: np.ndarray,
        ref_descriptors: np.ndarray
    ) -> Dict[str, Any]:
        """Standard feature matching using BFMatcher"""

        # Create BFMatcher object
        bf = cv2.BFMatcher(cv2.NORM_L2, crossCheck=True)

        # Match descriptors
        matches = bf.match(test_descriptors, ref_descriptors)

        # Sort matches by distance
        matches = sorted(matches, key=lambda x: x.distance)

        # Calculate confidence based on good matches
        good_matches = [m for m in matches if m.distance < 0.75]

        confidence = len(good_matches) / max(len(matches), 1) if matches else 0

        return {
            "method": "standard_bf",
            "total_matches": len(matches),
            "good_matches": len(good_matches),
            "confidence": confidence,
            "best_match_distance": matches[0].distance if matches else None
        }

    def _cds_similarity_matching(
        self,
        test_keypoints: List[cv2.KeyPoint],
        test_descriptors: np.ndarray,
        ref_keypoints: List[cv2.KeyPoint],
        ref_descriptors: np.ndarray,
        test_image: np.ndarray,
        ref_image: np.ndarray
    ) -> Dict[str, Any]:
        """Context-Dependent Similarity matching using CDS kernel"""

        try:
            # Step 1: Compute adjacency matrices for context
            test_adjacency = self._compute_adjacency_matrix(test_keypoints, test_image.shape)
            ref_adjacency = self._compute_adjacency_matrix(ref_keypoints, ref_image.shape)

            # Step 2: Initial matching using descriptor similarity
            bf = cv2.BFMatcher(cv2.NORM_L2, crossCheck=False)

            # Find k nearest neighbors
            matches = bf.knnMatch(test_descriptors, ref_descriptors, k=2)

            # Apply ratio test
            good_matches = []
            for m, n in matches:
                if m.distance < 0.75 * n.distance:
                    good_matches.append(m)

            if len(good_matches) < 4:
                return {
                    "method": "cds",
                    "confidence": 0,
                    "reason": "Insufficient good matches"
                }

            # Step 3: Compute CDS similarity scores
            similarity_scores = self._compute_cds_similarity(
                test_keypoints, ref_keypoints, good_matches,
                test_adjacency, ref_adjacency
            )

            # Step 4: Apply entropy regularization and thresholding
            final_confidence = self._apply_entropy_regularization(similarity_scores)

            return {
                "method": "cds",
                "total_matches": len(good_matches),
                "similarity_scores": similarity_scores,
                "confidence": final_confidence,
                "context_consistency": np.mean(similarity_scores) if similarity_scores else 0
            }

        except Exception as e:
            logger.error(f"Error in CDS matching: {e}")
            # Fallback to standard matching
            return self._standard_feature_matching(test_descriptors, ref_descriptors)

    def _compute_adjacency_matrix(
        self,
        keypoints: List[cv2.KeyPoint],
        image_shape: Tuple[int, int]
    ) -> np.ndarray:
        """Compute adjacency matrix based on spatial relationships"""

        n = len(keypoints)
        adjacency = np.zeros((n, n))

        for i in range(n):
            for j in range(n):
                if i != j:
                    # Compute spatial distance
                    pt1 = np.array(keypoints[i].pt)
                    pt2 = np.array(keypoints[j].pt)

                    distance = np.linalg.norm(pt1 - pt2)

                    # Compute orientation difference
                    angle_diff = abs(keypoints[i].angle - keypoints[j].angle)
                    angle_diff = min(angle_diff, 360 - angle_diff)

                    # Compute scale ratio
                    scale_ratio = keypoints[i].size / keypoints[j].size

                    # Combine factors for adjacency weight
                    spatial_weight = np.exp(-distance / 100)  # Distance threshold
                    orientation_weight = np.exp(-angle_diff / 45)  # Angle threshold
                    scale_weight = np.exp(-abs(np.log(scale_ratio)) / 0.5)  # Scale threshold

                    adjacency[i, j] = spatial_weight * orientation_weight * scale_weight

        return adjacency

    def _compute_cds_similarity(
        self,
        test_keypoints: List[cv2.KeyPoint],
        ref_keypoints: List[cv2.KeyPoint],
        matches: List[cv2.DMatch],
        test_adjacency: np.ndarray,
        ref_adjacency: np.ndarray
    ) -> List[float]:
        """Compute CDS similarity scores"""

        similarity_scores = []

        for match in matches:
            test_idx = match.queryIdx
            ref_idx = match.trainIdx

            # Fidelity term (descriptor similarity)
            fidelity = np.exp(-match.distance / 100)  # Convert distance to similarity

            # Context coherence term
            test_neighbors = np.where(test_adjacency[test_idx] > 0.1)[0]
            ref_neighbors = np.where(ref_adjacency[ref_idx] > 0.1)[0]

            context_coherence = 0
            if len(test_neighbors) > 0 and len(ref_neighbors) > 0:
                # Find corresponding neighbors through matches
                neighbor_similarities = []

                for test_neighbor in test_neighbors:
                    # Find match for this neighbor
                    neighbor_match = next(
                        (m for m in matches if m.queryIdx == test_neighbor), None
                    )
                    if neighbor_match:
                        ref_neighbor = neighbor_match.trainIdx
                        if ref_neighbor in ref_neighbors:
                            # Check if adjacency weights are similar
                            weight_similarity = 1 - abs(
                                test_adjacency[test_idx, test_neighbor] -
                                ref_adjacency[ref_idx, ref_neighbor]
                            )
                            neighbor_similarities.append(weight_similarity)

                if neighbor_similarities:
                    context_coherence = np.mean(neighbor_similarities)

            # Combine fidelity and context
            cds_score = fidelity * (0.7 + 0.3 * context_coherence)
            similarity_scores.append(cds_score)

        return similarity_scores

    def _apply_entropy_regularization(self, similarity_scores: List[float]) -> float:
        """Apply entropy regularization to determine final confidence"""

        if not similarity_scores:
            return 0

        # Convert to numpy array
        scores = np.array(similarity_scores)

        # Normalize scores
        if scores.max() > scores.min():
            scores = (scores - scores.min()) / (scores.max() - scores.min())

        # Compute entropy
        hist, _ = np.histogram(scores, bins=10, range=(0, 1))
        hist = hist / hist.sum()
        entropy = -np.sum(hist * np.log2(hist + 1e-10))

        # Normalize entropy (max entropy for uniform distribution is log2(10) ≈ 3.32)
        normalized_entropy = entropy / 3.32

        # High entropy means uncertain matching, low entropy means confident matching
        confidence = 1 - normalized_entropy

        # Also consider the number of good matches
        match_weight = min(len(similarity_scores) / 10, 1.0)  # Max at 10 matches

        final_confidence = confidence * match_weight

        return float(final_confidence)

    async def verify_logo_authenticity(
        self,
        image: np.ndarray,
        expected_manufacturer: str,
        logo_region: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Verify logo authenticity against expected manufacturer"""

        try:
            # Extract logo region if specified
            if logo_region:
                bbox = logo_region["bbox"]
                x, y, w, h = bbox
                logo_image = image[y:y+h, x:x+w]
            else:
                logo_image = image

            # Detect logo
            detection_result = await self.detect_logo(logo_image, expected_manufacturer)

            # Additional authenticity checks
            authenticity_checks = self._perform_authenticity_checks(
                logo_image, expected_manufacturer, detection_result
            )

            return {
                **detection_result,
                "authenticity_checks": authenticity_checks,
                "overall_authenticity_score": self._calculate_authenticity_score(
                    detection_result, authenticity_checks
                )
            }

        except Exception as e:
            logger.error(f"Error in logo authenticity verification: {e}")
            return {
                "detected": False,
                "confidence": 0,
                "error": str(e)
            }

    def _perform_authenticity_checks(
        self,
        logo_image: np.ndarray,
        manufacturer: str,
        detection_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Perform additional authenticity checks on detected logo"""

        checks = {
            "size_consistency": self._check_logo_size_consistency(logo_image, manufacturer),
            "shape_integrity": self._check_logo_shape_integrity(logo_image),
            "edge_sharpness": self._check_edge_sharpness(logo_image),
            "color_consistency": self._check_color_consistency(logo_image, manufacturer),
            "printing_quality": self._assess_printing_quality(logo_image)
        }

        return checks

    def _check_logo_size_consistency(self, logo_image: np.ndarray, manufacturer: str) -> Dict[str, float]:
        """Check if logo size is consistent with manufacturer standards"""

        height, width = logo_image.shape[:2]
        area = height * width

        # Expected size ranges (these would be calibrated per manufacturer)
        expected_ranges = {
            "STMicroelectronics": (1000, 10000),
            "Texas Instruments": (800, 8000),
            "NXP": (900, 9000),
            # Add more manufacturers as needed
        }

        expected_min, expected_max = expected_ranges.get(manufacturer, (500, 15000))

        if expected_min <= area <= expected_max:
            score = 0.9
            status = "consistent"
        elif area < expected_min * 0.5 or area > expected_max * 2:
            score = 0.2
            status = "severely_inconsistent"
        else:
            score = 0.6
            status = "moderately_inconsistent"

        return {"score": score, "status": status, "detected_area": area}

    def _check_logo_shape_integrity(self, logo_image: np.ndarray) -> Dict[str, float]:
        """Check if logo shape is intact"""

        # Use edge detection to assess shape integrity
        edges = cv2.Canny(logo_image, 50, 150)
        edge_density = np.sum(edges > 0) / edges.size

        # Good logos have clear, continuous edges
        if edge_density > 0.1:  # Sufficient edges
            score = 0.8
            status = "good_integrity"
        elif edge_density > 0.05:
            score = 0.6
            status = "moderate_integrity"
        else:
            score = 0.3
            status = "poor_integrity"

        return {"score": score, "status": status, "edge_density": edge_density}

    def _check_edge_sharpness(self, logo_image: np.ndarray) -> Dict[str, float]:
        """Check sharpness of logo edges"""

        # Use Laplacian variance as sharpness measure
        if len(logo_image.shape) == 3:
            gray = cv2.cvtColor(logo_image, cv2.COLOR_BGR2GRAY)
        else:
            gray = logo_image

        sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()

        # Higher values indicate sharper edges
        if sharpness > 100:
            score = 0.9
            status = "sharp"
        elif sharpness > 50:
            score = 0.7
            status = "moderately_sharp"
        else:
            score = 0.4
            status = "blurry"

        return {"score": score, "status": status, "sharpness_value": sharpness}

    def _check_color_consistency(self, logo_image: np.ndarray, manufacturer: str) -> Dict[str, float]:
        """Check if logo colors are consistent"""

        if len(logo_image.shape) == 3:
            # Convert to HSV for better color analysis
            hsv = cv2.cvtColor(logo_image, cv2.COLOR_BGR2HSV)

            # Calculate color statistics
            hue_std = np.std(hsv[:, :, 0])
            sat_std = np.std(hsv[:, :, 1])
            val_std = np.std(hsv[:, :, 2])

            # Low variance in color channels indicates consistent printing
            color_consistency = 1 - min((hue_std + sat_std + val_std) / 300, 1)

            if color_consistency > 0.8:
                score = 0.9
                status = "consistent"
            elif color_consistency > 0.6:
                score = 0.7
                status = "moderately_consistent"
            else:
                score = 0.5
                status = "inconsistent"
        else:
            # Grayscale image - can't check color consistency
            score = 0.5
            status = "cannot_assess"
            color_consistency = 0

        return {
            "score": score,
            "status": status,
            "color_consistency": color_consistency
        }

    def _assess_printing_quality(self, logo_image: np.ndarray) -> Dict[str, float]:
        """Assess overall printing quality"""

        # Combine multiple quality metrics
        if len(logo_image.shape) == 3:
            gray = cv2.cvtColor(logo_image, cv2.COLOR_BGR2GRAY)
        else:
            gray = logo_image

        # Noise assessment
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        noise = np.mean(np.abs(gray.astype(float) - blur.astype(float)))

        # Contrast assessment
        contrast = gray.std()

        # Overall quality score
        quality_score = min((contrast / 50) * (1 - noise / 50), 1)

        if quality_score > 0.8:
            score = 0.9
            status = "high_quality"
        elif quality_score > 0.6:
            score = 0.7
            status = "good_quality"
        else:
            score = 0.5
            status = "poor_quality"

        return {
            "score": score,
            "status": status,
            "noise_level": noise,
            "contrast": contrast,
            "overall_quality": quality_score
        }

    def _calculate_authenticity_score(
        self,
        detection_result: Dict[str, Any],
        authenticity_checks: Dict[str, Any]
    ) -> float:
        """Calculate overall authenticity score"""

        if not detection_result.get("detected", False):
            return 0.0

        # Base score from detection confidence
        base_score = detection_result.get("confidence", 0)

        # Weight authenticity checks
        check_weights = {
            "size_consistency": 0.15,
            "shape_integrity": 0.2,
            "edge_sharpness": 0.2,
            "color_consistency": 0.15,
            "printing_quality": 0.3
        }

        weighted_checks = 0
        total_weight = 0

        for check_name, weight in check_weights.items():
            if check_name in authenticity_checks:
                check_score = authenticity_checks[check_name].get("score", 0)
                weighted_checks += check_score * weight
                total_weight += weight

        if total_weight > 0:
            checks_score = weighted_checks / total_weight
        else:
            checks_score = 0

        # Combine detection confidence with authenticity checks
        overall_score = (base_score * 0.6) + (checks_score * 0.4)

        return min(overall_score, 1.0)

    async def add_reference_logo(
        self,
        manufacturer: str,
        logo_image: np.ndarray,
        save_to_disk: bool = True
    ) -> bool:
        """Add a new reference logo for a manufacturer"""

        try:
            # Extract features
            keypoints, descriptors = self._extract_sift_features(logo_image)

            if descriptors is None or len(descriptors) < 4:
                logger.error(f"Insufficient features in logo for {manufacturer}")
                return False

            # Cache in memory
            self.reference_logos[manufacturer] = {
                "image": logo_image,
                "keypoints": keypoints,
                "descriptors": descriptors
            }

            # Save to disk if requested
            if save_to_disk:
                logo_dir = os.path.join(os.getcwd(), "data", "logos")
                os.makedirs(logo_dir, exist_ok=True)

                logo_path = os.path.join(logo_dir, f"{manufacturer.lower()}_logo.jpg")
                cv2.imwrite(logo_path, logo_image)
                self.reference_logos[manufacturer]["path"] = logo_path

            logger.info(f"Added reference logo for {manufacturer}")
            return True

        except Exception as e:
            logger.error(f"Error adding reference logo for {manufacturer}: {e}")
            return False
