"""
Dimension Measurement Service for IC Chips.
Wrapper around the dimension measurement algorithm for backend integration.
With automatic pin-based calibration for accurate measurements.
"""
import cv2
import numpy as np
from typing import Optional, Dict, Tuple, List
import logging
import sys
import os

# Add dimensions folder to path for importing the measurement module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'dimensions'))

from ic_dimension_measurement import (
    preprocess_image,
    detect_ic_body,
    detect_ic_body_enhanced,
    compute_mm_per_pixel,
    create_visualization
)

logger = logging.getLogger(__name__)


# Standard pin pitches for different IC packages (in mm)
PIN_PITCH_MM = {
    'DIP': 2.54,      # Dual Inline Package (0.1 inch)
    'SOIC': 1.27,     # Small Outline IC (0.05 inch)  
    'SSOP': 0.65,     # Shrink Small Outline Package
    'TSSOP': 0.65,    # Thin Shrink Small Outline Package
    'QFP': 0.8,       # Quad Flat Package (varies 0.5-1.0)
    'QFN': 0.5,       # Quad Flat No-leads
    'PLCC': 1.27,     # Plastic Leaded Chip Carrier
    'DEFAULT': 2.54,  # Default to DIP pitch
}


class DimensionService:
    """Service for measuring IC chip dimensions from images."""
    
    # Default camera parameters (adjust based on your actual camera)
    DEFAULT_FOCAL_LENGTH_MM = 3.04      # Typical for many cameras
    DEFAULT_SENSOR_HEIGHT_MM = 2.74     # 1/4" sensor
    DEFAULT_CAMERA_HEIGHT_MM = 120.0    # Fixed at 12cm as per spec
    
    @staticmethod
    def _detect_pins_and_calculate_pitch(image: np.ndarray, ic_contour: np.ndarray) -> Optional[float]:
        """
        Detect IC pins and calculate mm_per_pixel using standard pin pitch.
        
        This function:
        1. Detects metallic pins at the edges of the IC
        2. Measures pixel distance between adjacent pins
        3. Uses standard DIP pin pitch (2.54mm) to calculate mm_per_pixel
        
        Returns:
            mm_per_pixel if pins detected, None otherwise
        """
        try:
            # Get bounding rect of IC
            x, y, w, h = cv2.boundingRect(ic_contour)
            
            # Determine if IC is horizontal or vertical (pins on long edges)
            is_horizontal = w > h
            
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Apply edge detection
            edges = cv2.Canny(gray, 50, 150)
            
            # Find all contours
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Filter for pin-like contours (small, near edges)
            pin_contours = []
            for cnt in contours:
                area = cv2.contourArea(cnt)
                px, py, pw, ph = cv2.boundingRect(cnt)
                
                # Pins are small rectangular shapes
                if area < 50:  # Too small
                    continue
                if area > w * h * 0.05:  # Too big (> 5% of IC area)
                    continue
                    
                # Pins should be at the edges of the IC
                # Check if contour is near top/bottom edge (for horizontal IC)
                # or near left/right edge (for vertical IC)
                cx, cy = px + pw/2, py + ph/2
                
                if is_horizontal:
                    # Pins on top or bottom
                    if cy < y + h * 0.2 or cy > y + h * 0.8:
                        pin_contours.append((cx, cy, cnt))
                else:
                    # Pins on left or right
                    if cx < x + w * 0.2 or cx > x + w * 0.8:
                        pin_contours.append((cx, cy, cnt))
            
            if len(pin_contours) < 2:
                print(f"[AUTO-CAL] Only found {len(pin_contours)} pin candidates, need at least 2")
                return None
            
            # Sort pins by position (x for horizontal IC, y for vertical)
            if is_horizontal:
                pin_contours.sort(key=lambda p: p[0])  # Sort by x
            else:
                pin_contours.sort(key=lambda p: p[1])  # Sort by y
            
            # Calculate distances between adjacent pins
            pin_distances = []
            for i in range(1, len(pin_contours)):
                if is_horizontal:
                    dist = abs(pin_contours[i][0] - pin_contours[i-1][0])
                else:
                    dist = abs(pin_contours[i][1] - pin_contours[i-1][1])
                
                # Filter out outliers (distances that are too small or too large)
                if dist > 5 and dist < 200:  # Reasonable pixel range for pin spacing
                    pin_distances.append(dist)
            
            if len(pin_distances) < 1:
                print("[AUTO-CAL] Could not find valid pin spacing")
                return None
            
            # Use median distance to be robust against outliers
            median_pin_distance_px = np.median(pin_distances)
            
            # Assume DIP package with 2.54mm pitch (most common for through-hole ICs)
            # For SMD ICs, this would need to be adjusted based on package type
            pin_pitch_mm = PIN_PITCH_MM['DIP']
            
            mm_per_pixel = pin_pitch_mm / median_pin_distance_px
            
            print(f"[AUTO-CAL] Detected {len(pin_distances)} pin spacings")
            print(f"[AUTO-CAL] Median pin distance: {median_pin_distance_px:.1f} pixels")
            print(f"[AUTO-CAL] Using pin pitch: {pin_pitch_mm}mm (DIP)")
            print(f"[AUTO-CAL] Calculated mm_per_pixel: {mm_per_pixel:.6f}")
            
            return mm_per_pixel
            
        except Exception as e:
            print(f"[AUTO-CAL] Pin detection failed: {e}")
            return None
    
    @staticmethod
    def _auto_calibrate_from_image(image: np.ndarray, ic_contour: np.ndarray, 
                                    rotated_rect: Tuple) -> float:
        """
        Automatically calibrate mm_per_pixel using IC size heuristics.
        
        Key insight: Most ICs are between 5mm and 50mm in their largest dimension.
        We use this knowledge along with package type heuristics to estimate mm_per_pixel.
        """
        (center_x, center_y), (width_px, height_px), angle = rotated_rect
        
        # Ensure width >= height
        if width_px < height_px:
            width_px, height_px = height_px, width_px
        
        # Calculate aspect ratio to guess package type
        aspect_ratio = width_px / height_px if height_px > 0 else 1
        
        # Estimate IC dimensions based on aspect ratio and typical sizes
        # Most ICs fall into these categories:
        
        if 2.5 < aspect_ratio < 4.5:
            # DIP package (long and narrow) - DIP-8, DIP-14, DIP-16, etc.
            # DIP-8: ~9.5mm x 6.4mm
            # DIP-14: ~19.3mm x 6.4mm  
            # DIP-16: ~19.3mm x 6.4mm
            # Use DIP-14 as reference (most common)
            estimated_width_mm = 19.3
            estimated_height_mm = 6.4
            print(f"[AUTO-CAL] Detected DIP-like package (aspect={aspect_ratio:.2f})")
            
        elif 1.8 < aspect_ratio <= 2.5:
            # SOIC or similar - wider body
            # SOIC-8: ~5mm x 4mm
            # SOIC-14: ~8.6mm x 4mm
            # SOIC-16: ~10mm x 4mm
            estimated_width_mm = 10.0
            estimated_height_mm = 4.0
            print(f"[AUTO-CAL] Detected SOIC-like package (aspect={aspect_ratio:.2f})")
            
        elif 0.8 < aspect_ratio <= 1.8:
            # Square-ish package - QFP, QFN, PLCC, or large power module
            # Could be 7x7mm to 20x20mm
            # Use 10mm as middle estimate
            estimated_width_mm = 15.0
            estimated_height_mm = 15.0 / aspect_ratio
            print(f"[AUTO-CAL] Detected square package (aspect={aspect_ratio:.2f})")
            
        else:
            # Unusual shape - use conservative estimate
            estimated_width_mm = 20.0
            estimated_height_mm = 20.0 / aspect_ratio
            print(f"[AUTO-CAL] Unknown package type (aspect={aspect_ratio:.2f}), using default")
        
        # Calculate mm_per_pixel from estimated dimensions
        mm_per_pixel_from_width = estimated_width_mm / width_px
        mm_per_pixel_from_height = estimated_height_mm / height_px
        
        # Average them for robustness
        mm_per_pixel = (mm_per_pixel_from_width + mm_per_pixel_from_height) / 2
        
        print(f"[AUTO-CAL] Estimated IC size: {estimated_width_mm:.1f}mm x {estimated_height_mm:.1f}mm")
        print(f"[AUTO-CAL] Pixel dimensions: {width_px:.0f}px x {height_px:.0f}px")
        print(f"[AUTO-CAL] Calculated mm_per_pixel: {mm_per_pixel:.6f}")
        
        # Sanity check: mm_per_pixel should be reasonable (0.01 to 0.5 for typical setups)
        if mm_per_pixel < 0.005:
            print(f"[AUTO-CAL] WARNING: mm_per_pixel too small ({mm_per_pixel:.6f}), clamping to 0.01")
            mm_per_pixel = 0.01
        elif mm_per_pixel > 0.5:
            print(f"[AUTO-CAL] WARNING: mm_per_pixel too large ({mm_per_pixel:.6f}), clamping to 0.1")
            mm_per_pixel = 0.1
            
        return mm_per_pixel
    
    @staticmethod
    def measure_from_bytes(
        image_bytes: bytes,
        mm_per_pixel: Optional[float] = None,
        focal_length_mm: Optional[float] = None,
        sensor_height_mm: Optional[float] = None,
        camera_height_mm: Optional[float] = None,
    ) -> Optional[Dict]:
        """
        Measure IC dimensions from image bytes.
        
        Args:
            image_bytes: Raw image bytes
            mm_per_pixel: Direct scaling factor (if known). If None, computed from camera params.
            focal_length_mm: Camera focal length
            sensor_height_mm: Camera sensor height  
            camera_height_mm: Camera height above object (fixed at 120mm)
            
        Returns:
            Dictionary with dimension data and visualization, or None if detection fails
        """
        # Apply defaults
        if focal_length_mm is None:
            focal_length_mm = DimensionService.DEFAULT_FOCAL_LENGTH_MM
        if sensor_height_mm is None:
            sensor_height_mm = DimensionService.DEFAULT_SENSOR_HEIGHT_MM
        if camera_height_mm is None:
            camera_height_mm = DimensionService.DEFAULT_CAMERA_HEIGHT_MM
            
        try:
            # Convert bytes to numpy array
            nparr = np.frombuffer(image_bytes, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if image is None:
                logger.error("Failed to decode image from bytes")
                return None
            
            return DimensionService._measure_image(
                image=image,
                mm_per_pixel=mm_per_pixel,
                focal_length_mm=focal_length_mm,
                sensor_height_mm=sensor_height_mm,
                camera_height_mm=camera_height_mm
            )
            
        except Exception as e:
            logger.error(f"Error measuring dimensions from bytes: {e}", exc_info=True)
            return None
    
    @staticmethod
    def measure_from_path(
        image_path: str,
        mm_per_pixel: Optional[float] = None,
        focal_length_mm: Optional[float] = None,
        sensor_height_mm: Optional[float] = None,
        camera_height_mm: Optional[float] = None,
    ) -> Optional[Dict]:
        """
        Measure IC dimensions from image file path.
        
        Args:
            image_path: Path to image file
            mm_per_pixel: Direct scaling factor (if known). If None, computed from camera params.
            focal_length_mm: Camera focal length
            sensor_height_mm: Camera sensor height
            camera_height_mm: Camera height above object (fixed at 120mm)
            
        Returns:
            Dictionary with dimension data and visualization, or None if detection fails
        """
        # Apply defaults
        if focal_length_mm is None:
            focal_length_mm = DimensionService.DEFAULT_FOCAL_LENGTH_MM
        if sensor_height_mm is None:
            sensor_height_mm = DimensionService.DEFAULT_SENSOR_HEIGHT_MM
        if camera_height_mm is None:
            camera_height_mm = DimensionService.DEFAULT_CAMERA_HEIGHT_MM
            
        try:
            image = cv2.imread(image_path)
            
            if image is None:
                logger.error(f"Failed to load image from path: {image_path}")
                return None
            
            return DimensionService._measure_image(
                image=image,
                mm_per_pixel=mm_per_pixel,
                focal_length_mm=focal_length_mm,
                sensor_height_mm=sensor_height_mm,
                camera_height_mm=camera_height_mm
            )
            
        except Exception as e:
            logger.error(f"Error measuring dimensions from path: {e}", exc_info=True)
            return None
    
    @staticmethod
    def _measure_image(
        image: np.ndarray,
        mm_per_pixel: Optional[float],
        focal_length_mm: float,
        sensor_height_mm: float,
        camera_height_mm: float,
    ) -> Optional[Dict]:
        """
        Internal method to measure IC dimensions from numpy array.
        
        Args:
            image: BGR image as numpy array
            mm_per_pixel: Direct scaling factor
            focal_length_mm: Camera focal length
            sensor_height_mm: Camera sensor height
            camera_height_mm: Camera height above object
            
        Returns:
            Dictionary with measurement results or None if detection fails
        """
        logger.info(f"Processing image: {image.shape[1]}x{image.shape[0]} pixels")
        
        # Step 1: Preprocess image
        preprocessed = preprocess_image(image, debug=False)
        
        # Step 2: Detect IC body (try standard first, then enhanced)
        ic_contour, rotated_rect = detect_ic_body(preprocessed, image, debug=False)
        
        if rotated_rect is None:
            logger.info("Standard detection failed, trying enhanced detection...")
            ic_contour, rotated_rect = detect_ic_body_enhanced(preprocessed, image, debug=False)
        
        if rotated_rect is None:
            logger.warning("Could not detect IC chip in image")
            return None
        
        # Step 3: Extract dimensions in pixels
        (center_x, center_y), (width_px, height_px), angle = rotated_rect
        
        # Ensure width >= height for consistency
        if width_px < height_px:
            width_px, height_px = height_px, width_px
        
        # Step 4: Compute or use mm_per_pixel
        if mm_per_pixel is None or mm_per_pixel <= 0:
            # Try auto-calibration from pin spacing
            print("[DIMENSION] Attempting auto-calibration...")
            mm_per_pixel = DimensionService._auto_calibrate_from_image(
                image, ic_contour, rotated_rect
            )
            print(f"[DIMENSION] Auto-calibrated mm_per_pixel: {mm_per_pixel:.6f}")
        
        # Step 5: Convert to millimeters
        width_mm = width_px * mm_per_pixel
        height_mm = height_px * mm_per_pixel
        area_mm2 = width_mm * height_mm
        
        print(f"[DIM_SVC] Dimensions: {width_mm:.2f}mm x {height_mm:.2f}mm, area={area_mm2:.2f}mm²")
        
        # Step 6: Create visualization
        visualization = create_visualization(
            image, ic_contour, rotated_rect,
            width_mm, height_mm, width_px, height_px
        )
        print(f"[DIM_SVC] Visualization created")
        
        # Determine confidence based on detection quality
        # (could be enhanced with more sophisticated metrics)
        image_area = image.shape[0] * image.shape[1]
        contour_area = cv2.contourArea(ic_contour)
        coverage = contour_area / image_area
        
        if coverage > 0.1 and coverage < 0.8:
            confidence = "high"
        elif coverage > 0.05:
            confidence = "medium"
        else:
            confidence = "low"
        
        result = {
            'width_mm': round(width_mm, 2),
            'height_mm': round(height_mm, 2),
            'width_px': round(width_px, 1),
            'height_px': round(height_px, 1),
            'area_mm2': round(area_mm2, 2),
            'mm_per_pixel': round(mm_per_pixel, 6),
            'angle': round(angle, 2),
            'center': (round(center_x, 1), round(center_y, 1)),
            'confidence': confidence,
            'visualization': visualization
        }
        
        logger.info(f"Measurement complete: {width_mm:.2f}mm x {height_mm:.2f}mm ({confidence} confidence)")
        
        return result
    
    @staticmethod
    def save_visualization(visualization: np.ndarray, output_path: str) -> bool:
        """
        Save visualization image to file.
        
        Args:
            visualization: Annotated image as numpy array
            output_path: Path to save the image
            
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            cv2.imwrite(output_path, visualization)
            logger.info(f"Visualization saved to: {output_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save visualization: {e}")
            return False
    
    @staticmethod
    def visualization_to_bytes(visualization: np.ndarray, format: str = '.png') -> Optional[bytes]:
        """
        Convert visualization image to bytes.
        
        Args:
            visualization: Annotated image as numpy array
            format: Image format ('.png', '.jpg')
            
        Returns:
            Image bytes or None if encoding fails
        """
        try:
            success, encoded = cv2.imencode(format, visualization)
            if success:
                return encoded.tobytes()
            return None
        except Exception as e:
            logger.error(f"Failed to encode visualization: {e}")
            return None

