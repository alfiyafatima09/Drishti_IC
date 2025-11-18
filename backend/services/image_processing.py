"""
Image processing service for IC analysis
"""
import cv2
import numpy as np
import os
from typing import Dict, List, Any, Optional, Tuple
from PIL import Image, ImageEnhance, ImageFilter
import hashlib
import logging
from datetime import datetime
import uuid

from config.settings import settings

logger = logging.getLogger(__name__)


class ImageProcessingService:
    """Service for processing images of ICs"""

    def __init__(self):
        self.image_dir = os.path.join(os.getcwd(), "data", "images")
        self.processed_dir = os.path.join(os.getcwd(), "data", "processed")
        os.makedirs(self.image_dir, exist_ok=True)
        os.makedirs(self.processed_dir, exist_ok=True)

    async def process_image(
        self,
        image_content: bytes,
        filename: str,
        preprocess: bool = True,
        enhance_contrast: bool = False
    ) -> Dict[str, Any]:
        """Process uploaded image for IC analysis"""

        try:
            # Generate unique ID for this image
            image_id = str(uuid.uuid4())

            # Save original image
            original_path = os.path.join(self.image_dir, f"{image_id}_original.jpg")
            with open(original_path, "wb") as f:
                f.write(image_content)

            # Decode image
            nparr = np.frombuffer(image_content, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            if image is None:
                raise ValueError("Failed to decode image")

            processed_image = image.copy()

            # Apply preprocessing if requested
            if preprocess:
                processed_image = self._preprocess_image(processed_image)

            # Enhance contrast if requested
            if enhance_contrast:
                processed_image = self._enhance_contrast(processed_image)

            # Save processed image
            processed_path = os.path.join(self.processed_dir, f"{image_id}_processed.jpg")
            cv2.imwrite(processed_path, processed_image)

            # Extract basic metadata
            metadata = self._extract_metadata(image, processed_image)

            return {
                "image_id": image_id,
                "original_path": original_path,
                "processed_path": processed_path,
                "metadata": metadata,
                "preprocessing_applied": preprocess,
                "contrast_enhanced": enhance_contrast
            }

        except Exception as e:
            logger.error(f"Error processing image: {e}")
            raise

    def _preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """Apply basic preprocessing to improve IC detection"""

        # Convert to grayscale if needed
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        # Apply bilateral filter to reduce noise while keeping edges sharp
        filtered = cv2.bilateralFilter(gray, 9, 75, 75)

        # Enhance local contrast using CLAHE
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(filtered)

        # Apply morphological operations to clean up the image
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        cleaned = cv2.morphologyEx(enhanced, cv2.MORPH_CLOSE, kernel)

        return cleaned

    def _enhance_contrast(self, image: np.ndarray) -> np.ndarray:
        """Enhance image contrast"""

        # Convert to LAB color space for better contrast enhancement
        if len(image.shape) == 3:
            lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)

            # Apply CLAHE to L channel
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
            l_enhanced = clahe.apply(l)

            # Merge channels
            lab_enhanced = cv2.merge([l_enhanced, a, b])
            enhanced = cv2.cvtColor(lab_enhanced, cv2.COLOR_LAB2BGR)
        else:
            # Grayscale image
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(image)

        return enhanced

    def _extract_metadata(
        self,
        original_image: np.ndarray,
        processed_image: np.ndarray
    ) -> Dict[str, Any]:
        """Extract metadata from images"""

        return {
            "original_shape": original_image.shape,
            "processed_shape": processed_image.shape,
            "original_dtype": str(original_image.dtype),
            "brightness": float(np.mean(original_image)),
            "contrast": float(original_image.std()),
            "sharpness": float(cv2.Laplacian(processed_image.astype(np.uint8), cv2.CV_64F).var()),
            "processing_timestamp": datetime.utcnow().isoformat()
        }

    async def analyze_image(
        self,
        image_id: str,
        analysis_type: str = "full"
    ) -> Dict[str, Any]:
        """Perform detailed analysis on a processed image"""

        processed_path = os.path.join(self.processed_dir, f"{image_id}_processed.jpg")

        if not os.path.exists(processed_path):
            raise FileNotFoundError(f"Processed image not found: {image_id}")

        # Load processed image
        image = cv2.imread(processed_path, cv2.IMREAD_GRAYSCALE)

        results = {}

        if analysis_type in ["full", "text_regions"]:
            results["text_regions"] = self._detect_text_regions(image)

        if analysis_type in ["full", "logo_regions"]:
            results["logo_regions"] = self._detect_logo_regions(image)

        if analysis_type in ["full", "marking_regions"]:
            results["marking_regions"] = self._detect_marking_regions(image)

        if analysis_type in ["full", "quality_metrics"]:
            results["quality_metrics"] = self._calculate_quality_metrics(image)

        return {
            "image_id": image_id,
            "analysis_type": analysis_type,
            "results": results,
            "timestamp": datetime.utcnow().isoformat()
        }

    def _detect_text_regions(self, image: np.ndarray) -> List[Dict[str, Any]]:
        """Detect regions likely to contain text markings"""

        # Apply adaptive thresholding
        thresh = cv2.adaptiveThreshold(
            image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2
        )

        # Find contours
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        text_regions = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if 100 < area < 5000:  # Reasonable text region size
                x, y, w, h = cv2.boundingRect(contour)
                aspect_ratio = w / h if h > 0 else 0

                # Text regions are usually wider than tall
                if 1.5 < aspect_ratio < 10:
                    text_regions.append({
                        "bbox": [x, y, w, h],
                        "area": area,
                        "aspect_ratio": aspect_ratio,
                        "confidence": min(1.0, area / 1000)
                    })

        # Sort by confidence
        text_regions.sort(key=lambda x: x["confidence"], reverse=True)
        return text_regions[:10]  # Return top 10 regions

    def _detect_logo_regions(self, image: np.ndarray) -> List[Dict[str, Any]]:
        """Detect regions likely to contain manufacturer logos"""

        # Use template matching or feature detection for logos
        # This is a simplified version - real implementation would use SIFT/SURF

        # Apply Canny edge detection
        edges = cv2.Canny(image, 50, 150)

        # Find contours
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        logo_regions = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if 500 < area < 10000:  # Logo region size
                x, y, w, h = cv2.boundingRect(contour)
                aspect_ratio = w / h if h > 0 else 0

                # Logos are often square or slightly rectangular
                if 0.7 < aspect_ratio < 1.5:
                    logo_regions.append({
                        "bbox": [x, y, w, h],
                        "area": area,
                        "aspect_ratio": aspect_ratio,
                        "confidence": min(1.0, area / 5000)
                    })

        logo_regions.sort(key=lambda x: x["confidence"], reverse=True)
        return logo_regions[:5]

    def _detect_marking_regions(self, image: np.ndarray) -> List[Dict[str, Any]]:
        """Detect IC marking regions (part numbers, dates, etc.)"""

        # Combine text and logo detection for comprehensive marking detection
        text_regions = self._detect_text_regions(image)
        logo_regions = self._detect_logo_regions(image)

        # Merge overlapping regions and filter
        all_regions = text_regions + logo_regions

        # Simple non-maximum suppression
        filtered_regions = []
        for region in all_regions:
            x, y, w, h = region["bbox"]
            overlaps = False

            for existing in filtered_regions:
                ex, ey, ew, eh = existing["bbox"]
                if (x < ex + ew and x + w > ex and
                    y < ey + eh and y + h > ey):
                    overlaps = True
                    break

            if not overlaps:
                filtered_regions.append(region)

        return filtered_regions

    def _calculate_quality_metrics(self, image: np.ndarray) -> Dict[str, float]:
        """Calculate image quality metrics for IC analysis"""

        # Brightness
        brightness = np.mean(image)

        # Contrast
        contrast = image.std()

        # Sharpness (Laplacian variance)
        sharpness = cv2.Laplacian(image, cv2.CV_64F).var()

        # Entropy (measure of information content)
        hist = cv2.calcHist([image], [0], None, [256], [0, 256])
        hist = hist / hist.sum()
        entropy = -np.sum(hist * np.log2(hist + 1e-10))

        # Signal-to-noise ratio approximation
        signal = np.mean(image)
        noise = np.std(image)
        snr = signal / noise if noise > 0 else 0

        return {
            "brightness": float(brightness),
            "contrast": float(contrast),
            "sharpness": float(sharpness),
            "entropy": float(entropy),
            "snr": float(snr),
            "overall_quality": float((brightness/128) * (contrast/50) * (sharpness/500) * (entropy/7))
        }

    async def extract_regions(
        self,
        image_id: str,
        region_type: str
    ) -> List[Dict[str, Any]]:
        """Extract specific types of regions from processed image"""

        analysis = await self.analyze_image(image_id, region_type)
        return analysis["results"].get(region_type, [])

    async def compare_images(
        self,
        ref_content: bytes,
        test_content: bytes,
        comparison_type: str = "similarity"
    ) -> Dict[str, Any]:
        """Compare two images"""

        # Decode images
        ref_arr = np.frombuffer(ref_content, np.uint8)
        test_arr = np.frombuffer(test_content, np.uint8)

        ref_img = cv2.imdecode(ref_arr, cv2.IMREAD_GRAYSCALE)
        test_img = cv2.imdecode(test_arr, cv2.IMREAD_GRAYSCALE)

        if ref_img is None or test_img is None:
            raise ValueError("Failed to decode one or both images")

        # Resize images to same size for comparison
        height = min(ref_img.shape[0], test_img.shape[0])
        width = min(ref_img.shape[1], test_img.shape[1])

        ref_resized = cv2.resize(ref_img, (width, height))
        test_resized = cv2.resize(test_img, (width, height))

        if comparison_type == "similarity":
            # Structural Similarity Index (SSIM)
            ssim_score = self._calculate_ssim(ref_resized, test_resized)

            # Mean Squared Error
            mse_score = np.mean((ref_resized.astype(float) - test_resized.astype(float)) ** 2)

            return {
                "comparison_type": "similarity",
                "ssim_score": float(ssim_score),
                "mse_score": float(mse_score),
                "similarity_percentage": float(ssim_score * 100)
            }

        elif comparison_type == "difference":
            # Calculate absolute difference
            diff = cv2.absdiff(ref_resized, test_resized)
            diff_mean = np.mean(diff)

            return {
                "comparison_type": "difference",
                "mean_difference": float(diff_mean),
                "max_difference": float(np.max(diff)),
                "difference_image_shape": diff.shape
            }

        else:
            raise ValueError(f"Unsupported comparison type: {comparison_type}")

    def _calculate_ssim(self, img1: np.ndarray, img2: np.ndarray) -> float:
        """Calculate Structural Similarity Index (simplified implementation)"""
        
        try:
            # Try to use scikit-image if available
            from skimage.metrics import structural_similarity as ssim
            return ssim(img1, img2)
        except ImportError:
            # Fallback to simple correlation-based similarity
            # Normalize images
            img1_norm = (img1 - img1.mean()) / (img1.std() + 1e-10)
            img2_norm = (img2 - img2.mean()) / (img2.std() + 1e-10)
            
            # Calculate correlation coefficient
            correlation = np.corrcoef(img1_norm.flatten(), img2_norm.flatten())[0, 1]
            
            # Convert to 0-1 range (correlation is -1 to 1)
            similarity = (correlation + 1) / 2
            
            return float(similarity)

    def get_image_path(self, image_id: str) -> str:
        """Get path to processed image"""
        return os.path.join(self.processed_dir, f"{image_id}_processed.jpg")

    async def delete_image(self, image_id: str):
        """Delete processed image and related files"""

        original_path = os.path.join(self.image_dir, f"{image_id}_original.jpg")
        processed_path = os.path.join(self.processed_dir, f"{image_id}_processed.jpg")

        for path in [original_path, processed_path]:
            if os.path.exists(path):
                os.remove(path)

    async def get_image_metadata(self, image_id: str) -> Dict[str, Any]:
        """Get metadata for a processed image"""

        processed_path = os.path.join(self.processed_dir, f"{image_id}_processed.jpg")

        if not os.path.exists(processed_path):
            raise FileNotFoundError(f"Image not found: {image_id}")

        # Get file stats
        stat = os.stat(processed_path)

        # Load image for analysis
        image = cv2.imread(processed_path, cv2.IMREAD_GRAYSCALE)

        return {
            "image_id": image_id,
            "file_size_bytes": stat.st_size,
            "created_time": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "modified_time": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "image_shape": image.shape if image is not None else None,
            "quality_metrics": self._calculate_quality_metrics(image) if image is not None else None
        }
