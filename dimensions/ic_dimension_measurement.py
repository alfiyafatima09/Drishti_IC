"""
Automated Optical Inspection (AOI) Tool for IC Chip Dimension Measurement
==================================    if debug and ic_contour is not None:
        debug_img = original.copy()
        cv2.drawContours(debug_img, [ic_contour], -1, (0, 255, 0), 3)
        
        # Draw all contours in red for comparison
        cv2.drawContours(debug_img, contours, -1, (0, 0, 255), 1)
        
        # Draw rotated bounding box
        box = cv2.boxPoints(rotated_rect)
        box = np.asarray(box, dtype=np.int32)
        cv2.drawContours(debug_img, [box], 0, (255, 0, 0), 2)
        
        cv2.imshow("5. Edges (Canny)", edges)
        cv2.imshow("6. Closed Edges", closed)
        cv2.imshow("7. Detected Entire IC Chip", debug_img)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    
    return ic_contour, rotated_rect====================

This module provides functions to measure the physical dimensions of IC chips
from top-down images, INCLUDING metallic pins (full chip dimensions).

Author: AOI System
Date: December 2025
"""

import cv2
import numpy as np
from typing import Tuple, Optional, Dict
import math


# ============================================================================
# 1. IMAGE PREPROCESSING
# ============================================================================

def preprocess_image(image: np.ndarray, debug: bool = False) -> np.ndarray:
    """
    Preprocess the IC chip image for contour detection.
    
    Steps:
    1. Convert to grayscale
    2. Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
    3. Apply bilateral filter to reduce noise while preserving edges
    4. Apply median blur for additional smoothing
    
    Args:
        image: Input BGR image
        debug: If True, display intermediate results
        
    Returns:
        Preprocessed grayscale image
    """
    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Apply CLAHE for better contrast
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    
    # Apply bilateral filter to reduce noise while keeping edges sharp
    bilateral = cv2.bilateralFilter(enhanced, d=9, sigmaColor=75, sigmaSpace=75)
    
    # Apply median blur for additional noise reduction
    blurred = cv2.medianBlur(bilateral, 5)
    
    if debug:
        cv2.imshow("1. Original Grayscale", gray)
        cv2.imshow("2. CLAHE Enhanced", enhanced)
        cv2.imshow("3. Bilateral Filtered", bilateral)
        cv2.imshow("4. Final Preprocessed", blurred)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    
    return blurred


# ============================================================================
# 2. IC BODY DETECTION
# ============================================================================

def detect_ic_body(preprocessed: np.ndarray, original: np.ndarray, 
                   debug: bool = False) -> Tuple[Optional[np.ndarray], Optional[Tuple]]:
    """
    Detect the entire IC chip contour (including pins) and fit a rotated bounding box.
    
    This function:
    1. Applies Canny edge detection
    2. Applies morphological closing to merge edges
    3. Finds all contours
    4. Filters contours to find the entire IC chip (including pins)
    5. Uses convex hull to encompass pins
    6. Fits a minimum area rotated rectangle
    
    Args:
        preprocessed: Preprocessed grayscale image
        original: Original BGR image (for visualization)
        debug: If True, display intermediate results
        
    Returns:
        Tuple of (IC chip contour, rotated rectangle parameters)
        rotated_rect format: ((center_x, center_y), (width, height), angle)
    """
    # Apply Canny edge detection
    # Use adaptive thresholds based on image statistics
    median_val = np.median(preprocessed)
    lower = int(max(0, 0.5 * median_val))  # More sensitive (was 0.66)
    upper = int(min(255, 1.5 * median_val))  # More sensitive (was 1.33)
    edges = cv2.Canny(preprocessed, lower, upper)
    
    # Apply morphological closing to connect nearby edges
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))  # Larger kernel (was 5x5)
    closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=3)  # More iterations (was 2)
    
    # Dilate slightly to strengthen edges
    dilated = cv2.dilate(closed, kernel, iterations=2)  # More dilation (was 1)
    
    # Find all contours
    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if len(contours) == 0:
        print("Error: No contours found in image")
        return None, None
    
    # Filter and select the IC body contour
    ic_contour, rotated_rect = _select_ic_body_contour(contours, original.shape)
    
    if debug and ic_contour is not None:
        debug_img = original.copy()
        cv2.drawContours(debug_img, [ic_contour], -1, (0, 255, 0), 3)
        
        # Draw all contours in red for comparison
        cv2.drawContours(debug_img, contours, -1, (0, 0, 255), 1)
        
        # Draw rotated bounding box
        box = cv2.boxPoints(rotated_rect)
        box = np.intp(box)  # Use np.intp instead of np.int0 for numpy 2.x compatibility
        cv2.drawContours(debug_img, [box], 0, (255, 0, 0), 2)
        
        cv2.imshow("5. Edges (Canny)", edges)
        cv2.imshow("6. Closed Edges", closed)
        cv2.imshow("7. Detected IC Body", debug_img)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    
    return ic_contour, rotated_rect


def _select_ic_body_contour(contours: list, image_shape: Tuple) -> Tuple[Optional[np.ndarray], Optional[Tuple]]:
    """
    Select the contour that represents the ENTIRE IC chip, INCLUDING pins.
    
    Strategy:
    1. Filter by area: IC should be reasonably large (> 0.5% of image area)
    2. Find the largest contour
    3. Use convex hull to encompass the entire IC including pins
    4. Fit rotated bounding box to get full dimensions
    
    Args:
        contours: List of all contours found
        image_shape: Shape of the image (height, width, channels)
        
    Returns:
        Tuple of (selected contour, rotated rectangle)
    """
    image_area = image_shape[0] * image_shape[1]
    min_area = image_area * 0.005  # IC should be at least 0.5% of image
    max_area = image_area * 0.9    # But not more than 90%
    
    valid_contours = []
    
    # Debug: print all contours info
    print(f"Found {len(contours)} contours, analyzing...")
    
    for i, contour in enumerate(contours):
        area = cv2.contourArea(contour)
        
        # Filter by area
        if area < min_area or area > max_area:
            continue
        
        # Calculate contour properties
        perimeter = cv2.arcLength(contour, True)
        if perimeter == 0:
            continue
        
        # Get convex hull to include all pins
        hull = cv2.convexHull(contour)
        hull_area = cv2.contourArea(hull)
        
        # Use hull for bounding box calculations
        x, y, w, h = cv2.boundingRect(hull)
        extent = hull_area / (w * h) if (w * h) > 0 else 0
        
        # Aspect ratio
        aspect_ratio = max(w, h) / min(w, h) if min(w, h) > 0 else 0
        
        # For entire IC chip (including pins):
        # - Should be roughly rectangular (relaxed extent)
        # - Not too elongated (reasonable aspect ratio)
        if extent > 0.40 and aspect_ratio < 5:
            valid_contours.append((hull, hull_area, extent, aspect_ratio))
            print(f"  Contour {i}: area={hull_area:.0f} ({hull_area/image_area*100:.1f}%), extent={extent:.2f}, aspect={aspect_ratio:.2f} ✓")
        else:
            if area >= min_area * 5:  # Only print larger rejected contours
                print(f"  Contour {i}: area={hull_area:.0f} ({hull_area/image_area*100:.1f}%), extent={extent:.2f}, aspect={aspect_ratio:.2f} ✗")
    
    if len(valid_contours) == 0:
        print("Error: No valid IC chip contour found")
        print(f"Tried {len(contours)} contours with criteria: extent>0.40, aspect<5")
        return None, None
    
    # Select the largest valid contour (most likely to be entire IC chip)
    valid_contours.sort(key=lambda x: x[1], reverse=True)
    ic_contour = valid_contours[0][0]
    
    print(f"Selected entire IC chip contour (convex hull) with area={valid_contours[0][1]:.0f}")
    
    # Fit minimum area rotated rectangle to convex hull (captures full IC with pins)
    rotated_rect = cv2.minAreaRect(ic_contour)
    
    return ic_contour, rotated_rect


def detect_ic_body_enhanced(preprocessed: np.ndarray, original: np.ndarray,
                            debug: bool = False) -> Tuple[Optional[np.ndarray], Optional[Tuple]]:
    """
    Enhanced multi-pass detection for difficult ICs (LQFN/QFN packages).
    
    This function tries multiple edge detection strategies:
    1. Standard Canny with current preprocessing
    2. More aggressive Canny with relaxed filtering
    3. Very aggressive with minimal filtering
    
    Args:
        preprocessed: Preprocessed grayscale image
        original: Original BGR image
        debug: If True, display intermediate results
        
    Returns:
        Tuple of (IC chip contour, rotated rectangle parameters)
    """
    image_area = original.shape[0] * original.shape[1]
    
    # Try multiple detection strategies with progressively relaxed criteria
    strategies = [
        {
            'name': 'Relaxed Detection',
            'canny_lower': 30,
            'canny_upper': 100,
            'close_size': 7,
            'close_iters': 3,
            'min_area_pct': 0.3,
            'extent_threshold': 0.35,
            'aspect_threshold': 6
        },
        {
            'name': 'Aggressive Detection',
            'canny_lower': 20,
            'canny_upper': 80,
            'close_size': 9,
            'close_iters': 4,
            'min_area_pct': 0.2,
            'extent_threshold': 0.30,
            'aspect_threshold': 7
        },
        {
            'name': 'Very Aggressive',
            'canny_lower': 15,
            'canny_upper': 60,
            'close_size': 11,
            'close_iters': 5,
            'min_area_pct': 0.15,
            'extent_threshold': 0.25,
            'aspect_threshold': 8
        }
    ]
    
    print(f"  Enhanced multi-pass detection for LQFN/QFN packages...")
    
    for strategy in strategies:
        print(f"    Trying: {strategy['name']}")
        
        # Edge detection
        edges = cv2.Canny(preprocessed, strategy['canny_lower'], strategy['canny_upper'])
        
        # Morphological closing
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, 
                                          (strategy['close_size'], strategy['close_size']))
        closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, 
                                 iterations=strategy['close_iters'])
        dilated = cv2.dilate(closed, kernel, iterations=1)
        
        # Find contours
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if len(contours) == 0:
            print(f"      → No contours found")
            continue
        
        # Filter contours
        min_area = image_area * (strategy['min_area_pct'] / 100)
        max_area = image_area * 0.9
        
        valid_contours = []
        
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < min_area or area > max_area:
                continue
            
            hull = cv2.convexHull(contour)
            hull_area = cv2.contourArea(hull)
            
            x, y, w, h = cv2.boundingRect(hull)
            extent = hull_area / (w * h) if (w * h) > 0 else 0
            aspect_ratio = max(w, h) / min(w, h) if min(w, h) > 0 else 0
            
            if extent > strategy['extent_threshold'] and aspect_ratio < strategy['aspect_threshold']:
                valid_contours.append((hull, hull_area, extent, aspect_ratio))
        
        if len(valid_contours) > 0:
            # Success!
            valid_contours.sort(key=lambda x: x[1], reverse=True)
            ic_contour = valid_contours[0][0]
            
            print(f"      ✓ Found {len(valid_contours)} valid contour(s)")
            print(f"      ✓ Selected: area={valid_contours[0][1]:.0f} ({valid_contours[0][1]/image_area*100:.1f}%), "
                  f"extent={valid_contours[0][2]:.2f}, aspect={valid_contours[0][3]:.2f}")
            
            rotated_rect = cv2.minAreaRect(ic_contour)
            
            if debug:
                debug_img = original.copy()
                cv2.drawContours(debug_img, [ic_contour], -1, (0, 255, 0), 3)
                box = cv2.boxPoints(rotated_rect)
                box = np.asarray(box, dtype=np.int32)
                cv2.drawContours(debug_img, [box], 0, (255, 0, 0), 2)
                cv2.imshow(f"Enhanced Detection: {strategy['name']}", debug_img)
                cv2.waitKey(0)
                cv2.destroyAllWindows()
            
            return ic_contour, rotated_rect
        else:
            print(f"      → No valid contours")
    
    # All strategies failed
    print("  ✗ All enhanced detection strategies failed")
    return None, None


# ============================================================================
# 3. PIXEL-TO-MILLIMETER CONVERSION
# ============================================================================

def compute_mm_per_pixel(image_height_px: int,
                         focal_length_mm: float = 3.04,
                         sensor_height_mm: float = 2.74,
                         camera_height_mm: float = 120.0) -> float:
    """
    Compute mm per pixel using the pinhole camera projection model.
    
    Formula:
        mm_per_pixel = (sensor_height_mm * camera_height_mm) / (image_height_px * focal_length_mm)
    
    This represents the ground sampling distance (GSD) - how many millimeters
    in the real world correspond to one pixel in the image.
    
    Args:
        image_height_px: Height of the image in pixels
        focal_length_mm: Focal length of the camera lens (default: 3.04mm, typical for many cameras)
        sensor_height_mm: Physical height of the camera sensor (default: 2.74mm for 1/4" sensor)
        camera_height_mm: Height of camera above the object (fixed at 120mm as per spec)
        
    Returns:
        mm_per_pixel: The scaling factor
        
    Common sensor sizes:
        - 1/4" sensor: 3.2 x 2.4 mm (diagonal ~4mm)
        - 1/3" sensor: 4.8 x 3.6 mm (diagonal ~6mm)
        - 1/2.5" sensor: 5.76 x 4.29 mm (diagonal ~7.2mm)
    """
    mm_per_pixel = (sensor_height_mm * camera_height_mm) / (image_height_px * focal_length_mm)
    return mm_per_pixel


def calibrate_from_checkerboard(checkerboard_image_path: str,
                                 square_size_mm: float,
                                 pattern_size: Tuple[int, int] = (9, 6)) -> Dict:
    """
    Perform camera calibration using a checkerboard pattern.
    
    This is a more accurate method to determine camera parameters.
    Use this for one-time calibration of your camera setup.
    
    Args:
        checkerboard_image_path: Path to checkerboard calibration image
        square_size_mm: Size of each checkerboard square in millimeters
        pattern_size: Number of inner corners (columns, rows)
        
    Returns:
        Dictionary with calibration parameters including mm_per_pixel
    """
    image = cv2.imread(checkerboard_image_path)
    if image is None:
        raise ValueError(f"Could not load calibration image: {checkerboard_image_path}")
    
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Find checkerboard corners
    ret, corners = cv2.findChessboardCorners(gray, pattern_size, None)
    
    if not ret:
        raise ValueError("Could not find checkerboard corners in calibration image")
    
    # Refine corner positions
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
    corners_refined = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)
    
    # Prepare object points (real-world coordinates)
    objp = np.zeros((pattern_size[0] * pattern_size[1], 3), np.float32)
    objp[:, :2] = np.mgrid[0:pattern_size[0], 0:pattern_size[1]].T.reshape(-1, 2)
    objp *= square_size_mm
    
    # Camera calibration
    ret, camera_matrix, dist_coeffs, rvecs, tvecs = cv2.calibrateCamera(
        [objp], [corners_refined], gray.shape[::-1], None, None
    )
    
    # Extract focal length
    fx = camera_matrix[0, 0]  # Focal length in x (pixels)
    fy = camera_matrix[1, 1]  # Focal length in y (pixels)
    
    # Compute mm per pixel from known square size
    # Average distance between corners in pixels
    pixel_distances = []
    for i in range(len(corners_refined) - 1):
        dist = np.linalg.norm(corners_refined[i] - corners_refined[i + 1])
        pixel_distances.append(dist)
    
    avg_pixel_dist = np.mean(pixel_distances)
    mm_per_pixel = square_size_mm / avg_pixel_dist
    
    return {
        'mm_per_pixel': mm_per_pixel,
        'camera_matrix': camera_matrix,
        'dist_coeffs': dist_coeffs,
        'focal_length_px': (fx, fy)
    }


# ============================================================================
# 4. MAIN MEASUREMENT FUNCTION
# ============================================================================

def measure_ic_dimensions(image_path: str,
                         mm_per_pixel: Optional[float] = None,
                         focal_length_mm: float = 3.04,
                         sensor_height_mm: float = 2.74,
                         camera_height_mm: float = 120.0,
                         debug: bool = False,
                         enhanced_mode: bool = False) -> Dict:
    """
    Main function to measure the entire IC chip dimensions (including pins).
    
    Args:
        image_path: Path to the IC chip image
        mm_per_pixel: Direct scaling factor (if known). If None, will compute using camera params.
        focal_length_mm: Camera focal length (used if mm_per_pixel is None)
        sensor_height_mm: Camera sensor height (used if mm_per_pixel is None)
        camera_height_mm: Camera height above object (fixed at 120mm)
        debug: If True, show intermediate processing steps
        enhanced_mode: If True, use multi-pass detection with relaxed criteria (better for LQFN/QFN)
        
    Returns:
        Dictionary containing:
            - width_mm: Width in millimeters (including pins)
            - height_mm: Height in millimeters (including pins)
            - width_px: Width in pixels
            - height_px: Height in pixels
            - mm_per_pixel: Scaling factor used
            - visualization: Image with annotations
    """
    # Load image
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"Could not load image: {image_path}")
    
    print(f"\nProcessing: {image_path}")
    print(f"Image size: {image.shape[1]} x {image.shape[0]} pixels")
    
    # Step 1: Preprocess image
    preprocessed = preprocess_image(image, debug=debug)
    
    # Step 2: Detect entire IC chip (including pins)
    ic_contour, rotated_rect = detect_ic_body(preprocessed, image, debug=debug)
    
    # If detection failed and enhanced_mode not explicitly requested, try enhanced detection
    if rotated_rect is None and not enhanced_mode:
        print("Standard detection failed. Trying enhanced LQFN/QFN detection...")
        enhanced_mode = True
    
    # Step 2b: Enhanced multi-pass detection for difficult ICs (LQFN/QFN)
    if enhanced_mode:
        ic_contour, rotated_rect = detect_ic_body_enhanced(preprocessed, image, debug=debug)
    
    if rotated_rect is None:
        raise ValueError("Could not detect IC chip in image")
    
    # Step 3: Extract dimensions in pixels
    (center_x, center_y), (width_px, height_px), angle = rotated_rect
    
    # Ensure width >= height for consistency
    if width_px < height_px:
        width_px, height_px = height_px, width_px
    
    # Step 4: Compute or use mm_per_pixel
    if mm_per_pixel is None:
        mm_per_pixel = compute_mm_per_pixel(
            image_height_px=image.shape[0],
            focal_length_mm=focal_length_mm,
            sensor_height_mm=sensor_height_mm,
            camera_height_mm=camera_height_mm
        )
        print(f"Computed mm_per_pixel: {mm_per_pixel:.6f} mm/px")
    else:
        print(f"Using provided mm_per_pixel: {mm_per_pixel:.6f} mm/px")
    
    # Step 5: Convert to millimeters
    width_mm = width_px * mm_per_pixel
    height_mm = height_px * mm_per_pixel
    
    # Step 6: Create visualization
    visualization = create_visualization(image, ic_contour, rotated_rect, 
                                        width_mm, height_mm, width_px, height_px)
    
    return {
        'width_mm': width_mm,
        'height_mm': height_mm,
        'width_px': width_px,
        'height_px': height_px,
        'mm_per_pixel': mm_per_pixel,
        'visualization': visualization,
        'angle': angle,
        'center': (center_x, center_y)
    }


# ============================================================================
# 5. VISUALIZATION
# ============================================================================

def create_visualization(image: np.ndarray,
                        contour: np.ndarray,
                        rotated_rect: Tuple,
                        width_mm: float,
                        height_mm: float,
                        width_px: float,
                        height_px: float) -> np.ndarray:
    """
    Create a visualization image with entire IC chip contour and measurements.
    
    Args:
        image: Original BGR image
        contour: IC chip contour (convex hull including pins)
        rotated_rect: Rotated rectangle parameters
        width_mm, height_mm: Dimensions in millimeters (including pins)
        width_px, height_px: Dimensions in pixels
        
    Returns:
        Annotated image
    """
    vis = image.copy()
    
    # Draw IC chip contour in green (includes pins)
    cv2.drawContours(vis, [contour], -1, (0, 255, 0), 3)
    
    # Draw rotated bounding box in blue
    box = cv2.boxPoints(rotated_rect)
    box = np.intp(box)  # Use np.intp instead of np.int0 for numpy 2.x compatibility
    cv2.drawContours(vis, [box], 0, (255, 0, 0), 2)
    
    # Draw center point
    center_x, center_y = int(rotated_rect[0][0]), int(rotated_rect[0][1])
    cv2.circle(vis, (center_x, center_y), 5, (0, 0, 255), -1)
    
    # Add text annotations
    font = cv2.FONT_HERSHEY_SIMPLEX
    text_y = 30
    line_height = 35
    
    # Add semi-transparent background for text
    overlay = vis.copy()
    cv2.rectangle(overlay, (10, 10), (550, 130), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.6, vis, 0.4, 0, vis)
    
    cv2.putText(vis, f"IC Chip Width:  {width_mm:.2f} mm ({width_px:.1f} px)", 
                (20, text_y), font, 0.7, (0, 255, 255), 2)
    cv2.putText(vis, f"IC Chip Height: {height_mm:.2f} mm ({height_px:.1f} px)", 
                (20, text_y + line_height), font, 0.7, (0, 255, 255), 2)
    cv2.putText(vis, f"Area: {width_mm * height_mm:.2f} mm² (with pins)", 
                (20, text_y + 2*line_height), font, 0.7, (0, 255, 255), 2)
    
    return vis


# ============================================================================
# 6. UTILITY FUNCTIONS
# ============================================================================

def print_results(results: Dict):
    """
    Print measurement results in the specified format.
    
    Args:
        results: Dictionary returned by measure_ic_dimensions()
    """
    print("\n" + "="*60)
    print("IC CHIP DIMENSION MEASUREMENT RESULTS (Including Pins)")
    print("="*60)
    print(f"IC Chip Width:  {results['width_mm']:.2f} mm ({results['width_px']:.1f} px)")
    print(f"IC Chip Height: {results['height_mm']:.2f} mm ({results['height_px']:.1f} px)")
    print(f"Area:           {results['width_mm'] * results['height_mm']:.2f} mm²")
    print(f"Scaling Factor: {results['mm_per_pixel']:.6f} mm/px")
    print(f"Rotation Angle: {results['angle']:.2f}°")
    print("="*60 + "\n")


def save_results(results: Dict, output_path: str):
    """
    Save the visualization image.
    
    Args:
        results: Dictionary returned by measure_ic_dimensions()
        output_path: Path to save the visualization image
    """
    cv2.imwrite(output_path, results['visualization'])
    print(f"Visualization saved to: {output_path}")


# ============================================================================
# MAIN EXECUTION (Example Usage)
# ============================================================================

if __name__ == "__main__":
    """
    Example usage demonstrating both measurement methods:
    Method A: Using direct mm_per_pixel value
    Method B: Using camera calibration parameters
    """
    
    # Example 1: Using direct mm_per_pixel (if you have calibrated your system)
    print("\n" + "="*60)
    print("METHOD A: Using Direct mm_per_pixel Value")
    print("="*60)
    
    # For example, if you measured that 1mm = 50 pixels in your setup:
    # results_a = measure_ic_dimensions(
    #     image_path="images/001.png",
    #     mm_per_pixel=1.0/50.0,  # 0.02 mm per pixel
    #     debug=False
    # )
    # print_results(results_a)
    # save_results(results_a, "output_method_a.png")
    
    
    # Example 2: Using camera calibration parameters (pinhole model)
    print("\n" + "="*60)
    print("METHOD B: Using Camera Calibration Parameters")
    print("="*60)
    
    results_b = measure_ic_dimensions(
        image_path="images/001.png",
        mm_per_pixel=None,  # Will compute from camera parameters
        focal_length_mm=3.04,      # Adjust based on your camera
        sensor_height_mm=2.74,     # Adjust based on your camera sensor
        camera_height_mm=120.0,    # Fixed at 12 cm as specified
        debug=False
    )
    print_results(results_b)
    save_results(results_b, "output_method_b.png")
    
    # Display results
    cv2.imshow("IC Measurement Result", results_b['visualization'])
    print("Press any key to close the window...")
    cv2.waitKey(0)
    cv2.destroyAllWindows()
