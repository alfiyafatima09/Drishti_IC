"""
Image Classification Service for Model Selection

This service analyzes images to determine the best processing model based on:
- Image size and resolution
- Text density (OCR potential)
- Visual complexity (pin visibility, package type)
- Estimated processing requirements

Returns classification scores for routing to appropriate models.
"""

import os
from pathlib import Path
from typing import Dict, Any, List
from PIL import Image
import cv2
import numpy as np
import sys

# Add path for correct module
sys.path.insert(0, str(Path(__file__).parent / "correct"))

from backend.services.correct.classifier import detect_ic_pins_enhanced


class ImageClassifier:
    def __init__(self):
        self.text_density_threshold = 0.1  # Minimum text area ratio
        self.complexity_threshold = 0.3    # Minimum complexity for heavy models
        self.pin_visibility_threshold = 0.2  # Minimum pin visibility

    def classify_image(self, image_path: str) -> Dict[str, Any]:
        """
        Classify a single image for model selection.

        Returns:
            {
                'model_type': 'ocr_only' | 'light_vision' | 'heavy_vision' | 'full_pipeline',
                'confidence': float,
                'features': {...},
                'estimated_time': float  # seconds
            }
        """
        try:
            # Load image
            img = Image.open(image_path)
            img_cv = cv2.imread(image_path)

            if img_cv is None:
                raise ValueError(f"Could not load image: {image_path}")

            # Basic features
            width, height = img.size
            size_mb = os.path.getsize(image_path) / (1024 * 1024)

            # Text density estimation (rough OCR potential)
            gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            text_density = np.sum(thresh == 0) / (width * height)

            # Visual complexity (edge density)
            edges = cv2.Canny(gray, 50, 150)
            complexity = np.sum(edges > 0) / (width * height)

            # Pin visibility (rough estimate via contours)
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            pin_visibility = len(contours) / 1000  # Normalized

            # Get IC package classification
            package_result = detect_ic_pins_enhanced(image_path, debug=False)
            package_type = package_result['classification']
            sides_with_pins = package_result['sides_with_pins']
            
            # Brightness analysis for counterfeit detection
            brightness_metrics = self._analyze_brightness_for_counterfeit(gray)

            features = {
                'width': width,
                'height': height,
                'size_mb': size_mb,
                'text_density': text_density,
                'complexity': complexity,
                'pin_visibility': pin_visibility,
                'package_type': package_type,
                'sides_with_pins': sides_with_pins,
                'font_brightness': brightness_metrics['font_brightness'],
                'logo_brightness': brightness_metrics['logo_brightness'],
                'contrast': brightness_metrics['contrast'],
                'mean_brightness': brightness_metrics['mean_brightness']
            }

            # Model selection based on package type and features
            model_type, confidence, estimated_time = self._select_model(features)

            return {
                'model_type': model_type,
                'confidence': confidence,
                'features': features,
                'estimated_time': estimated_time
            }

        except Exception as e:
            return {
                'model_type': 'full_pipeline',  # Fallback
                'confidence': 0.5,
                'error': str(e),
                'estimated_time': 10.0,
                'features': {
                    'font_brightness': 0.0,
                    'logo_brightness': 0.0,
                    'contrast': 0.0,
                    'package_type': 'unknown'
                }
            }

    def _select_model(self, features: Dict[str, Any]) -> tuple[str, float, float]:
        """
        Select the best model based on features.

        Returns: (model_type, confidence, estimated_time)
        """
        package_type = features['package_type']
        text_density = features['text_density']
        complexity = features['complexity']
        pin_visibility = features['pin_visibility']

        # Model routing logic based on package type
        if package_type == 'LQFN':
            # LQFN: No pins, use annotate_mask_pins.py
            model_type = 'light_vision'
            confidence = 0.9
            estimated_time = 2.0
        elif package_type == 'QFN_SINGLE_SIDE':
            # Single side: Vision model for pin counting
            model_type = 'heavy_vision'
            confidence = 0.85
            estimated_time = 4.0
        elif package_type == 'QFN_DUAL_SIDE':
            # Dual side: Vision model
            model_type = 'heavy_vision'
            confidence = 0.85
            estimated_time = 5.0
        elif package_type == 'QFN_4_SIDE':
            # 4 sides: Use annotate_mask_pins.py
            model_type = 'light_vision'
            confidence = 0.9
            estimated_time = 3.0
        else:
            # Unknown: Full pipeline
            model_type = 'full_pipeline'
            confidence = 0.7
            estimated_time = 8.0

        # Adjust based on image features
        if text_density > self.text_density_threshold:
            # High text: OCR can help
            estimated_time *= 0.8
            confidence = min(confidence + 0.1, 1.0)

        if complexity > self.complexity_threshold:
            # High complexity: May need heavier processing
            if model_type == 'light_vision':
                model_type = 'heavy_vision'
                estimated_time *= 1.5

        return model_type, confidence, estimated_time

    def classify_batch(self, image_paths: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Classify multiple images in batch.

        Returns dict of image_path -> classification
        """
        results = {}
        for path in image_paths:
            results[path] = self.classify_image(path)
        return results
    
    def _analyze_brightness_for_counterfeit(self, gray: np.ndarray) -> Dict[str, float]:
        """
        Analyze image brightness to detect potential counterfeit indicators.
        
        Counterfeit ICs often have:
        - Overly bright/white markings (remarking with bright paint)
        - High contrast between text and package (unnatural looking)
        - Uniform bright areas (laser etching artifacts)
        
        Returns:
            Dict with brightness metrics for counterfeit detection
        """
        try:
            # Calculate overall mean brightness
            mean_brightness = float(np.mean(gray))
            
            # Calculate contrast (standard deviation)
            contrast = float(np.std(gray))
            
            # Find bright regions (potential text/logo areas)
            # Genuine IC markings typically have moderate brightness
            _, bright_mask = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)
            bright_pixels = gray[bright_mask > 0]
            
            # Calculate font brightness (bright text areas)
            font_brightness = float(np.mean(bright_pixels)) if len(bright_pixels) > 0 else 0.0
            
            # Check for very bright spots (potential remarking/laser etching)
            very_bright_pixels = gray[gray > 220]
            logo_brightness = float(np.mean(very_bright_pixels)) if len(very_bright_pixels) > 100 else 0.0
            
            # Calculate percentage of very bright pixels (>220)
            # Genuine ICs rarely have large uniformly bright areas
            bright_pixel_ratio = len(very_bright_pixels) / gray.size
            
            # Adjust brightness score if large bright areas detected
            if bright_pixel_ratio > 0.05:  # More than 5% very bright
                logo_brightness = max(logo_brightness, 210)  # Flag as suspicious
            
            return {
                'font_brightness': font_brightness,
                'logo_brightness': logo_brightness,
                'contrast': contrast,
                'mean_brightness': mean_brightness,
                'bright_pixel_ratio': bright_pixel_ratio
            }
        except Exception as e:
            print(f"Error in brightness analysis: {e}")
            return {
                'font_brightness': 0.0,
                'logo_brightness': 0.0,
                'contrast': 0.0,
                'mean_brightness': 0.0,
                'bright_pixel_ratio': 0.0
            }


# Example usage
if __name__ == "__main__":
    classifier = ImageClassifier()

    # Test with one image from batch
    test_image = "/home/knk/Documents/work/Drishti_IC/images/batch2/lm.jpeg"
    if os.path.exists(test_image):
        result = classifier.classify_image(test_image)
        print(f"Classification for {test_image}:")
        print(result)
    else:
        print("Test image not found")