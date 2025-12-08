"""
OCR service for IC chip text extraction.
Provides preprocessing and OCR functionality using PaddleOCR.
"""
import logging
from pathlib import Path
from typing import List, Tuple, Optional, Union
from dataclasses import dataclass
import io

import numpy as np
import cv2
from paddleocr import PaddleOCR

logger = logging.getLogger(__name__)


@dataclass
class OCRResult:
    """Result from OCR processing."""
    text: str
    confidence: float


@dataclass
class OCRResponse:
    """Complete OCR response with all detected text."""
    results: List[OCRResult]
    status: str
    error: Optional[str] = None
    
    @property
    def texts(self) -> List[str]:
        """Get just the text strings."""
        return [r.text for r in self.results]
    
    @property
    def full_text(self) -> str:
        """Get all text joined by newlines."""
        return "\n".join(self.texts)


class ICChipOCR:
    """
    OCR service for extracting text from IC chip images.
    
    Implements a 7-step preprocessing pipeline optimized for IC chips:
    1. Grayscale conversion
    2. Bilateral filtering (edge-preserving denoising)
    3. CLAHE (Contrast Limited Adaptive Histogram Equalization)
    4. Deskew (straighten rotated text)
    5. Auto-crop (remove excess borders)
    6. Resize to optimal height
    7. Final bilateral filtering
    """
    
    def __init__(
        self,
        target_height: int = 640,
        min_confidence: float = 0.5,
        fallback_confidence: float = 0.3
    ):
        """
        Initialize the OCR service.
        
        Args:
            target_height: Target height for image resizing (default: 640)
            min_confidence: Minimum confidence threshold for primary detection (default: 0.5)
            fallback_confidence: Confidence threshold for fallback detection (default: 0.3)
        """
        self.target_height = target_height
        self.min_confidence = min_confidence
        self.fallback_confidence = fallback_confidence
        self._ocr: Optional[PaddleOCR] = None
        logger.info(f"ICChipOCR initialized with target_height={target_height}, min_confidence={min_confidence}")
    
    @property
    def ocr(self) -> PaddleOCR:
        """Lazy-load PaddleOCR instance."""
        if self._ocr is None:
            logger.info("Initializing PaddleOCR engine...")
            self._ocr = PaddleOCR(use_textline_orientation=True, lang='en')
            logger.info("PaddleOCR engine initialized")
        return self._ocr
    
    def extract_text(
        self,
        image: Union[bytes, np.ndarray, Path, str],
        preprocess: bool = True
    ) -> OCRResponse:
        """
        Extract text from an IC chip image.
        
        Args:
            image: Input image as bytes, numpy array, or file path
            preprocess: Whether to apply the preprocessing pipeline (default: True)
            
        Returns:
            OCRResponse with extracted text results
        """
        try:
            # Load image to numpy array
            img_array = self._load_image(image)
            if img_array is None:
                return OCRResponse(
                    results=[],
                    status="error",
                    error="Failed to load image"
                )
            
            logger.info(f"Image loaded: shape={img_array.shape}, dtype={img_array.dtype}")
            
            if preprocess:
                preprocessed = self._preprocess(img_array)
            else:
                preprocessed = img_array
            
            # Run OCR
            results = self._run_ocr(preprocessed)
            
            if not results and preprocess:
                logger.info("No results with preprocessing, trying original image...")
                resized_orig = self._simple_resize(img_array)
                results = self._run_ocr(resized_orig, use_fallback_threshold=True)
            
            if results:
                logger.info(f"OCR completed: {len(results)} text segments found")
                return OCRResponse(results=results, status="success")
            else:
                logger.info("No text detected in image")
                return OCRResponse(results=[], status="success", error="No text detected")
                
        except Exception as e:
            logger.error(f"OCR extraction failed: {str(e)}", exc_info=True)
            return OCRResponse(
                results=[],
                status="error",
                error=str(e)
            )
    
    def _load_image(self, image: Union[bytes, np.ndarray, Path, str]) -> Optional[np.ndarray]:
        """
        Load image from various input types.
        
        Args:
            image: Image as bytes, numpy array, or file path
            
        Returns:
            Numpy array (BGR format) or None if loading failed
        """
        try:
            if isinstance(image, np.ndarray):
                return image
            
            if isinstance(image, bytes):
                nparr = np.frombuffer(image, np.uint8)
                img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                return img
            
            if isinstance(image, (Path, str)):
                path = Path(image)
                if not path.exists():
                    logger.error(f"Image file not found: {path}")
                    return None
                img = cv2.imread(str(path))
                return img
                
        except Exception as e:
            logger.error(f"Failed to load image: {str(e)}")
            return None
        
        return None
    
    def _preprocess(self, image: np.ndarray) -> np.ndarray:
        """
        Apply full 7-step preprocessing pipeline.
        
        Args:
            image: Input BGR image
            
        Returns:
            Preprocessed BGR image
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        filtered = cv2.bilateralFilter(gray, d=9, sigmaColor=75, sigmaSpace=75)
        
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(filtered)
        
        deskewed = self._deskew(enhanced)
        
        cropped = deskewed
        
        resized = self._resize_to_height(cropped, self.target_height)
        
        final = cv2.bilateralFilter(resized, d=5, sigmaColor=50, sigmaSpace=50)
        
        preprocessed = cv2.cvtColor(final, cv2.COLOR_GRAY2BGR)
        
        return preprocessed
    
    def _deskew(self, image: np.ndarray) -> np.ndarray:
        """
        Detect and correct rotation in image.
        
        Args:
            image: Grayscale input image
            
        Returns:
            Deskewed image
        """
        coords = np.column_stack(np.where(image > 0))
        if len(coords) == 0:
            return image
        
        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle
        
        if abs(angle) > 2.0:
            h, w = image.shape[:2]
            center = (w // 2, h // 2)
            M = cv2.getRotationMatrix2D(center, angle, 1.0)
            deskewed = cv2.warpAffine(
                image, M, (w, h),
                flags=cv2.INTER_CUBIC,
                borderMode=cv2.BORDER_REPLICATE
            )
            return deskewed
        
        return image
    
    def _resize_to_height(self, image: np.ndarray, target_height: int) -> np.ndarray:
        """
        Resize image to target height while maintaining aspect ratio.
        
        Args:
            image: Input image
            target_height: Target height in pixels
            
        Returns:
            Resized image
        """
        h, w = image.shape[:2]
        aspect_ratio = w / h
        new_width = int(target_height * aspect_ratio)
        return cv2.resize(image, (new_width, target_height), interpolation=cv2.INTER_CUBIC)
    
    def _simple_resize(self, image: np.ndarray) -> np.ndarray:
        """
        Simple resize without full preprocessing (for fallback).
        
        Args:
            image: Input BGR image
            
        Returns:
            Resized BGR image
        """
        h, w = image.shape[:2]
        aspect_ratio = w / h
        new_width = int(self.target_height * aspect_ratio)
        return cv2.resize(image, (new_width, self.target_height), interpolation=cv2.INTER_CUBIC)
    
    def _run_ocr(
        self,
        image: np.ndarray,
        use_fallback_threshold: bool = False
    ) -> List[OCRResult]:
        """
        Run PaddleOCR on image.
        
        Args:
            image: Preprocessed BGR image
            use_fallback_threshold: Use lower confidence threshold
            
        Returns:
            List of OCRResult
        """
        threshold = self.fallback_confidence if use_fallback_threshold else self.min_confidence

        # Prefer PaddleOCR.ocr (newer API); fallback to predict (older API)
        try:
            ocr_result = self.ocr.ocr(image, cls=True)
            results: List[OCRResult] = []
            if ocr_result and len(ocr_result) > 0:
                for line in ocr_result[0]:
                    if not line or len(line) < 2:
                        continue
                    text, score = line[1]
                    if text and text.strip() and score > threshold:
                        results.append(OCRResult(text=text.strip(), confidence=score))
            # Sort by confidence (desc) to make best line obvious
            results.sort(key=lambda r: r.confidence, reverse=True)
            return results
        except Exception as e:
            logger.debug(f"OCR .ocr() call failed, trying .predict(): {e}")

        try:
            result = self.ocr.predict(image)
            
            results = []
            if result and len(result) > 0:
                result_dict = result[0]
                rec_texts = result_dict.get('rec_texts', [])
                rec_scores = result_dict.get('rec_scores', [])
                
                for i in range(len(rec_texts)):
                    text = rec_texts[i]
                    score = rec_scores[i] if i < len(rec_scores) else 0.0
                    
                    # Filter by confidence and non-empty
                    if text and text.strip() and score > threshold:
                        results.append(OCRResult(text=text.strip(), confidence=score))
            
            results.sort(key=lambda r: r.confidence, reverse=True)
            return results
            
        except Exception as e:
            logger.error(f"OCR prediction failed: {str(e)}")
            return []


_ocr_service: Optional[ICChipOCR] = None


def get_ocr_service(
    target_height: int = 640,
    min_confidence: float = 0.5
) -> ICChipOCR:
    """
    Get or create the OCR service singleton.
    
    Args:
        target_height: Target height for image resizing
        min_confidence: Minimum confidence threshold
        
    Returns:
        ICChipOCR instance
    """
    global _ocr_service
    if _ocr_service is None:
        _ocr_service = ICChipOCR(
            target_height=target_height,
            min_confidence=min_confidence
        )
    return _ocr_service


def extract_text_from_image(
    image: Union[bytes, np.ndarray, Path, str],
    preprocess: bool = True,
    min_confidence: float = 0.5
) -> OCRResponse:
    """
    Convenience function to extract text from an image.
    
    Args:
        image: Input image as bytes, numpy array, or file path
        preprocess: Whether to apply preprocessing pipeline
        min_confidence: Minimum confidence threshold
        
    Returns:
        OCRResponse with extracted text
        
    Example:
        # From bytes
        with open("chip.jpg", "rb") as f:
            result = extract_text_from_image(f.read())
        
        # From file path
        result = extract_text_from_image("chip.jpg")
        
        # From numpy array
        img = cv2.imread("chip.jpg")
        result = extract_text_from_image(img)
        
        # Get results
        print(result.full_text)  # All text joined
        for r in result.results:
            print(f"{r.text} ({r.confidence:.2%})")
    """
    service = get_ocr_service(min_confidence=min_confidence)
    return service.extract_text(image, preprocess=preprocess)

