"""
Enhanced IC Dimension Measurement - LQFN/QFN Package Support
=============================================================

This module provides enhanced detection specifically optimized for:
- LQFN (Low-profile Quad Flat No-lead) packages
- QFN (Quad Flat No-lead) packages
- Other low-contrast IC packages

Key improvements:
1. Enhanced edge detection for low-contrast boundaries
2. Multiple preprocessing strategies
3. Multi-pass detection (strict → relaxed criteria)
4. Better handling of flat/recessed pins
"""

import cv2
import numpy as np
from typing import Tuple, Optional, Dict
from ic_dimension_measurement import (
    compute_mm_per_pixel, 
    create_visualization, 
    print_results,
    save_results
)


def preprocess_for_lqfn(image: np.ndarray, debug: bool = False) -> Tuple[np.ndarray, np.ndarray]:
    """
    Enhanced preprocessing specifically for LQFN/QFN packages.
    
    LQFN packages have:
    - Very flat pins (no protrusion)
    - Low contrast edges
    - Metallic surface variations
    - Small solder pads
    
    Strategy:
    1. Multiple contrast enhancement methods
    2. Morphological gradient for subtle edges
    3. Sharper edge detection
    
    Args:
        image: Input BGR image
        debug: If True, display intermediate results
        
    Returns:
        Tuple of (standard preprocessed, edge-enhanced preprocessed)
    """
    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # ====== Method 1: Standard CLAHE ======
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    enhanced1 = clahe.apply(gray)
    
    # ====== Method 2: Aggressive CLAHE for low contrast ======
    clahe_aggressive = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(4, 4))
    enhanced2 = clahe_aggressive.apply(gray)
    
    # ====== Method 3: Morphological Gradient (finds edges) ======
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    gradient = cv2.morphologyEx(enhanced1, cv2.MORPH_GRADIENT, kernel)
    
    # Enhance gradient
    gradient_enhanced = cv2.normalize(gradient, None, 0, 255, cv2.NORM_MINMAX)
    
    # ====== Standard path ======
    bilateral = cv2.bilateralFilter(enhanced1, d=9, sigmaColor=75, sigmaSpace=75)
    standard = cv2.medianBlur(bilateral, 5)
    
    # ====== Enhanced path (for LQFN) ======
    # Use adaptive histogram equalization
    enhanced_bilateral = cv2.bilateralFilter(enhanced2, d=7, sigmaColor=50, sigmaSpace=50)
    
    # Combine with gradient information
    combined = cv2.addWeighted(enhanced_bilateral, 0.7, gradient_enhanced, 0.3, 0)
    
    # Sharpen the combined image
    kernel_sharpen = np.array([[-1,-1,-1],
                               [-1, 9,-1],
                               [-1,-1,-1]])
    sharpened = cv2.filter2D(combined, -1, kernel_sharpen)
    
    # Final smoothing to reduce noise
    edge_enhanced = cv2.medianBlur(sharpened, 3)
    
    if debug:
        cv2.imshow("1. Original Gray", gray)
        cv2.imshow("2. Standard CLAHE", enhanced1)
        cv2.imshow("3. Aggressive CLAHE", enhanced2)
        cv2.imshow("4. Morphological Gradient", gradient_enhanced)
        cv2.imshow("5. Standard Preprocessing", standard)
        cv2.imshow("6. Edge-Enhanced (LQFN)", edge_enhanced)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    
    return standard, edge_enhanced


def detect_ic_multipass(preprocessed_images: list, 
                        original: np.ndarray,
                        debug: bool = False) -> Tuple[Optional[np.ndarray], Optional[Tuple]]:
    """
    Multi-pass detection strategy for difficult ICs.
    
    Tries multiple edge detection and filtering strategies:
    1. Standard Canny with strict filtering
    2. Aggressive Canny with relaxed filtering
    3. Combined approach with very relaxed filtering
    
    Args:
        preprocessed_images: List of preprocessed images to try
        original: Original BGR image
        debug: If True, display intermediate results
        
    Returns:
        Tuple of (IC contour, rotated rectangle)
    """
    image_area = original.shape[0] * original.shape[1]
    
    # Try multiple detection strategies
    strategies = [
        {
            'name': 'Standard Detection',
            'img_idx': 0,
            'canny_params': (50, 150),
            'close_kernel': (5, 5),
            'close_iters': 2,
            'min_area_pct': 0.5,
            'extent_threshold': 0.40,
            'aspect_threshold': 5
        },
        {
            'name': 'Enhanced Detection (LQFN)',
            'img_idx': 1,
            'canny_params': (30, 100),
            'close_kernel': (7, 7),
            'close_iters': 3,
            'min_area_pct': 0.3,
            'extent_threshold': 0.35,
            'aspect_threshold': 6
        },
        {
            'name': 'Aggressive Detection',
            'img_idx': 1,
            'canny_params': (20, 80),
            'close_kernel': (9, 9),
            'close_iters': 4,
            'min_area_pct': 0.2,
            'extent_threshold': 0.30,
            'aspect_threshold': 7
        }
    ]
    
    for strategy in strategies:
        print(f"  Trying: {strategy['name']}")
        
        # Select preprocessed image
        preprocessed = preprocessed_images[strategy['img_idx']]
        
        # Edge detection with strategy parameters
        edges = cv2.Canny(preprocessed, *strategy['canny_params'])
        
        # Morphological closing
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, strategy['close_kernel'])
        closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, 
                                  iterations=strategy['close_iters'])
        
        # Additional dilation to strengthen edges
        dilated = cv2.dilate(closed, kernel, iterations=1)
        
        # Find contours
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if len(contours) == 0:
            print(f"    → No contours found")
            continue
        
        # Filter contours
        min_area = image_area * (strategy['min_area_pct'] / 100)
        max_area = image_area * 0.9
        
        valid_contours = []
        
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < min_area or area > max_area:
                continue
            
            # Convex hull
            hull = cv2.convexHull(contour)
            hull_area = cv2.contourArea(hull)
            
            # Bounding rect
            x, y, w, h = cv2.boundingRect(hull)
            extent = hull_area / (w * h) if (w * h) > 0 else 0
            aspect_ratio = max(w, h) / min(w, h) if min(w, h) > 0 else 0
            
            # Apply filters
            if extent > strategy['extent_threshold'] and aspect_ratio < strategy['aspect_threshold']:
                valid_contours.append((hull, hull_area, extent, aspect_ratio))
        
        if len(valid_contours) > 0:
            # Success! Select largest
            valid_contours.sort(key=lambda x: x[1], reverse=True)
            ic_contour = valid_contours[0][0]
            
            print(f"    → Found {len(valid_contours)} valid contour(s)")
            print(f"    ✓ Selected: area={valid_contours[0][1]:.0f} ({valid_contours[0][1]/image_area*100:.1f}%), "
                  f"extent={valid_contours[0][2]:.2f}, aspect={valid_contours[0][3]:.2f}")
            
            # Fit rotated rectangle
            rotated_rect = cv2.minAreaRect(ic_contour)
            
            if debug:
                debug_img = original.copy()
                cv2.drawContours(debug_img, [ic_contour], -1, (0, 255, 0), 3)
                box = cv2.boxPoints(rotated_rect)
                box = np.intp(box)
                cv2.drawContours(debug_img, [box], 0, (255, 0, 0), 2)
                cv2.imshow(f"Detection: {strategy['name']}", debug_img)
                cv2.imshow(f"Edges: {strategy['name']}", dilated)
                cv2.waitKey(0)
                cv2.destroyAllWindows()
            
            return ic_contour, rotated_rect
        else:
            print(f"    → No valid contours passed filtering")
    
    # All strategies failed
    print("  ✗ All detection strategies failed")
    return None, None


def measure_ic_dimensions_enhanced(image_path: str,
                                   mm_per_pixel: Optional[float] = None,
                                   focal_length_mm: float = 3.04,
                                   sensor_height_mm: float = 2.74,
                                   camera_height_mm: float = 120.0,
                                   debug: bool = False) -> Dict:
    """
    Enhanced IC measurement with LQFN/QFN support.
    
    This function uses:
    - Enhanced preprocessing for low-contrast edges
    - Multi-pass detection strategy
    - Better handling of flat no-lead packages
    
    Args:
        image_path: Path to IC image
        mm_per_pixel: Direct scaling factor (optional)
        focal_length_mm: Camera focal length
        sensor_height_mm: Camera sensor height
        camera_height_mm: Camera height above object
        debug: Show intermediate steps
        
    Returns:
        Dictionary with measurement results
    """
    # Load image
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"Could not load image: {image_path}")
    
    print(f"\n{'='*70}")
    print(f"Enhanced LQFN/QFN Detection")
    print(f"{'='*70}")
    print(f"Processing: {image_path}")
    print(f"Image size: {image.shape[1]} x {image.shape[0]} pixels")
    
    # Step 1: Enhanced preprocessing
    print("\nStep 1: Enhanced Preprocessing")
    standard_prep, enhanced_prep = preprocess_for_lqfn(image, debug=debug)
    
    # Step 2: Multi-pass detection
    print("\nStep 2: Multi-Pass Detection")
    ic_contour, rotated_rect = detect_ic_multipass(
        [standard_prep, enhanced_prep],
        image,
        debug=debug
    )
    
    if rotated_rect is None:
        raise ValueError("Could not detect IC chip in image (tried all strategies)")
    
    # Step 3: Extract dimensions
    (center_x, center_y), (width_px, height_px), angle = rotated_rect
    
    # Ensure width >= height
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
        print(f"\nComputed mm_per_pixel: {mm_per_pixel:.6f} mm/px")
    else:
        print(f"\nUsing provided mm_per_pixel: {mm_per_pixel:.6f} mm/px")
    
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


if __name__ == "__main__":
    """
    Test enhanced detection on difficult LQFN images.
    """
    import sys
    
    # Test images
    test_images = [
        'images/new2.png',  # Failed with standard detection
        'images/002.png',   # LQFN
        'images/003.png',   # LQFN
    ]
    
    print("\n" + "="*70)
    print("Enhanced LQFN/QFN IC Detection Test")
    print("="*70)
    
    for img_path in test_images:
        try:
            results = measure_ic_dimensions_enhanced(
                image_path=img_path,
                mm_per_pixel=None,
                debug=False
            )
            
            print_results(results)
            
            # Save result
            output_name = img_path.replace('images/', 'enhanced_').replace('/', '_')
            save_results(results, output_name)
            print(f"✓ Saved: {output_name}\n")
            
        except Exception as e:
            print(f"\n✗ Failed: {e}\n")
            import traceback
            traceback.print_exc()
