#!/usr/bin/env python3
"""
IC Chip Physical Analysis Module
=================================

Extracts pin count and physical dimensions from IC chip images using
classical computer vision techniques (no machine learning required).

Features:
    - IC boundary detection using contour analysis
    - Pin counting on all four sides
    - Physical dimension estimation
    - Debug visualization outputs

Usage:
    python ic_physical_analysis.py <image_path> [--reference-pixels N] [--reference-mm M]

Author: Auto-generated for SIH Project
Date: 2025-11-29
"""

import sys
import os
import argparse
import numpy as np
import cv2
from typing import Tuple, Dict, Optional, List
from scipy.ndimage import gaussian_filter1d
from scipy.signal import find_peaks


def preprocess_for_ic_analysis(img: np.ndarray) -> np.ndarray:
    """
    Preprocess image for IC chip analysis using classical computer vision.
    
    Applies grayscale conversion, CLAHE contrast enhancement, bilateral
    filtering for denoising, edge detection, and morphological operations.
    
    Args:
        img (np.ndarray): Input BGR image
    
    Returns:
        np.ndarray: Processed edge-detected image
    """
    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    
    # Bilateral filter for edge-preserving denoising
    denoised = cv2.bilateralFilter(enhanced, d=9, sigmaColor=75, sigmaSpace=75)
    
    # Edge detection using Canny
    edges = cv2.Canny(denoised, threshold1=50, threshold2=150)
    
    # Morphological closing to connect edges
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=2)
    
    return closed


def detect_ic_boundary(img: np.ndarray, original_img: np.ndarray) -> Dict:
    """
    Detect IC chip boundary using contour detection and minimum area rectangle.
    
    Finds the largest contour, fits a minimum area rectangle, and extracts
    the chip's physical parameters.
    
    Args:
        img (np.ndarray): Preprocessed edge image
        original_img (np.ndarray): Original BGR image for visualization
    
    Returns:
        dict: Dictionary containing:
            - corners: 4 corner points of the rectangle
            - width_pixels: Width in pixels
            - height_pixels: Height in pixels
            - angle: Rotation angle
            - center: Center point (x, y)
            - box: cv2.minAreaRect result
    """
    # Find contours
    contours, _ = cv2.findContours(img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if not contours:
        raise ValueError("No contours found in the image")
    
    # Find the largest contour by area
    largest_contour = max(contours, key=cv2.contourArea)
    
    # Get minimum area rectangle
    rect = cv2.minAreaRect(largest_contour)
    box = cv2.boxPoints(rect)
    box = np.intp(box)
    
    # Extract parameters
    center, (width, height), angle = rect
    
    # Ensure width is always the longer dimension
    if width < height:
        width, height = height, width
        angle = angle + 90
    
    # Normalize angle to [-90, 0]
    if angle > 0:
        angle = angle - 90
    
    # Create visualization
    vis_img = original_img.copy()
    cv2.drawContours(vis_img, [box], 0, (0, 255, 0), 3)
    cv2.circle(vis_img, (int(center[0]), int(center[1])), 5, (0, 0, 255), -1)
    
    # Add labels
    cv2.putText(vis_img, f"IC Chip", (int(center[0] - 50), int(center[1] - 10)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    cv2.putText(vis_img, f"{int(width)}x{int(height)} px", 
                (int(center[0] - 50), int(center[1] + 20)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    
    # Save visualization
    cv2.imwrite("ic_boundary.jpg", vis_img)
    print("✓ Saved: ic_boundary.jpg")
    
    return {
        "corners": box,
        "width_pixels": int(width),
        "height_pixels": int(height),
        "angle": angle,
        "center": center,
        "box": rect
    }


def compute_dimensions_mm(
    width_pixels: int,
    height_pixels: int,
    reference_pixels: Optional[float] = None,
    reference_mm: Optional[float] = None
) -> Dict:
    """
    Compute physical dimensions in millimeters.
    
    If reference calibration is provided, converts pixels to mm.
    Otherwise, returns pixel dimensions.
    
    Args:
        width_pixels (int): Width in pixels
        height_pixels (int): Height in pixels
        reference_pixels (float, optional): Known reference length in pixels
        reference_mm (float, optional): Known reference length in mm
    
    Returns:
        dict: Dictionary containing:
            - length_mm: Length in mm (or pixels if no reference)
            - width_mm: Width in mm (or pixels if no reference)
            - aspect_ratio: Width/height ratio
            - pixels_per_mm: Conversion factor (if reference provided)
    """
    aspect_ratio = width_pixels / height_pixels if height_pixels > 0 else 0
    
    if reference_pixels and reference_mm:
        # Compute mm per pixel
        mm_per_pixel = reference_mm / reference_pixels
        length_mm = width_pixels * mm_per_pixel
        width_mm = height_pixels * mm_per_pixel
        
        return {
            "length_mm": round(length_mm, 2),
            "width_mm": round(width_mm, 2),
            "aspect_ratio": round(aspect_ratio, 2),
            "pixels_per_mm": round(1 / mm_per_pixel, 2)
        }
    else:
        # Return pixel dimensions
        return {
            "length_mm": None,
            "width_mm": None,
            "length_px": width_pixels,
            "width_px": height_pixels,
            "aspect_ratio": round(aspect_ratio, 2),
            "pixels_per_mm": None
        }


def extract_side_strip(
    img: np.ndarray,
    bbox: Tuple,
    side: str,
    strip_width: int = 30
) -> np.ndarray:
    """
    Extract a narrow strip from one side of the bounding box.
    
    Args:
        img (np.ndarray): Grayscale image
        bbox: Result from cv2.minAreaRect
        side (str): 'top', 'right', 'bottom', or 'left'
        strip_width (int): Width of the strip to extract
    
    Returns:
        np.ndarray: Extracted strip image
    """
    center, (w, h), angle = bbox
    
    # Get rotation matrix
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    
    # Rotate the entire image
    rotated = cv2.warpAffine(img, M, (img.shape[1], img.shape[0]),
                             flags=cv2.INTER_LINEAR)
    
    # Calculate crop region based on side
    cx, cy = int(center[0]), int(center[1])
    w, h = int(w), int(h)
    
    if side == 'top':
        x1, y1 = cx - w // 2, cy - h // 2 - strip_width
        x2, y2 = cx + w // 2, cy - h // 2 + strip_width
    elif side == 'bottom':
        x1, y1 = cx - w // 2, cy + h // 2 - strip_width
        x2, y2 = cx + w // 2, cy + h // 2 + strip_width
    elif side == 'left':
        x1, y1 = cx - w // 2 - strip_width, cy - h // 2
        x2, y2 = cx - w // 2 + strip_width, cy + h // 2
    elif side == 'right':
        x1, y1 = cx + w // 2 - strip_width, cy - h // 2
        x2, y2 = cx + w // 2 + strip_width, cy + h // 2
    else:
        raise ValueError(f"Invalid side: {side}")
    
    # Ensure coordinates are within image bounds
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(rotated.shape[1], x2), min(rotated.shape[0], y2)
    
    # Extract strip
    strip = rotated[y1:y2, x1:x2]
    
    return strip


def detect_pins_on_strip(
    strip: np.ndarray,
    side: str,
    min_distance: int = 15
) -> List[int]:
    """
    Detect pins on a single strip using edge detection and clustering.
    
    Args:
        strip (np.ndarray): Strip image
        side (str): 'top', 'bottom', 'left', or 'right'
        min_distance (int): Minimum distance between pins
    
    Returns:
        list: List of pin positions
    """
    if strip.size == 0:
        return []
    
    # Simple but effective approach: find dark regions (pins) against lighter background
    # Apply strong bilateral filter to preserve edges
    filtered = cv2.bilateralFilter(strip, 9, 75, 75)
    
    # Use Otsu thresholding to separate pins from background
    _, binary = cv2.threshold(filtered, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    
    # Clean up with morphological operations
    kernel_small = np.ones((2, 2), np.uint8)
    kernel_large = np.ones((3, 3), np.uint8)
    
    # Remove noise
    binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel_small)
    # Fill gaps
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel_large)
    
    # Project to 1D - sum the binary values along the appropriate axis
    if side in ['top', 'bottom']:
        projection = np.sum(binary, axis=0)  # Sum columns for horizontal pins
    else:
        projection = np.sum(binary, axis=1)  # Sum rows for vertical pins
    
    # Normalize
    if projection.max() > 0:
        projection = projection.astype(float) / projection.max()
    else:
        return []
    
    # Smooth the projection to reduce noise
    projection = gaussian_filter1d(projection, sigma=1.5)
    
    # Find peaks - these represent pin locations
    # Use stricter parameters to avoid false positives
    peaks, properties = find_peaks(
        projection,
        height=0.3,  # Must be at least 30% of max
        distance=min_distance,  # Minimum distance between pins
        prominence=0.15,  # Must stand out from surroundings
        width=2  # Must have some minimum width
    )
    
    return peaks.tolist()


def count_pins(img: np.ndarray, bbox: Tuple, strip_width: int = 30, min_distance: int = 20) -> Dict[str, int]:
    """
    Count pins on all four sides of the IC chip.
    
    Uses edge detection, Sobel operators, and clustering to identify
    individual pins on each side of the chip.
    
    Args:
        img (np.ndarray): Grayscale preprocessed image
        bbox: Minimum area rectangle from cv2.minAreaRect
        strip_width (int): Width of strip to analyze for pin detection
        min_distance (int): Minimum distance between detected pins
    
    Returns:
        dict: Pin counts for each side and total
            {
                "top": int,
                "right": int,
                "bottom": int,
                "left": int,
                "total": int
            }
    """
    sides = ['top', 'right', 'bottom', 'left']
    pin_counts = {}
    
    for side in sides:
        # Extract strip for this side with narrower width focused on pins
        strip = extract_side_strip(img, bbox, side, strip_width=strip_width)
        
        if strip.size == 0:
            pin_counts[side] = 0
            continue
        
        # Detect pins on this strip with configurable minimum distance
        pins = detect_pins_on_strip(strip, side, min_distance=min_distance)
        pin_counts[side] = len(pins)
        
        # Create debug visualization
        vis_strip = cv2.cvtColor(strip, cv2.COLOR_GRAY2BGR)
        
        # Draw detected pin locations
        if side in ['top', 'bottom']:
            for pin_pos in pins:
                cv2.line(vis_strip, (pin_pos, 0), (pin_pos, strip.shape[0]),
                        (0, 255, 0), 2)
        else:
            for pin_pos in pins:
                cv2.line(vis_strip, (0, pin_pos), (strip.shape[1], pin_pos),
                        (0, 255, 0), 2)
        
        # Add pin count text
        cv2.putText(vis_strip, f"Pins: {len(pins)}", (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        
        # Save debug image
        filename = f"pins_{side}.jpg"
        cv2.imwrite(filename, vis_strip)
        print(f"✓ Saved: {filename}")
    
    # Calculate total
    pin_counts['total'] = sum(pin_counts[side] for side in sides)
    
    return pin_counts


def print_results(
    dimensions: Dict,
    pin_counts: Dict[str, int],
    has_reference: bool = False
):
    """
    Pretty-print analysis results in the specified format.
    
    Args:
        dimensions (dict): Dimension measurements
        pin_counts (dict): Pin count results
        has_reference (bool): Whether mm measurements are available
    """
    print("\n" + "=" * 60)
    print("IC CHIP ANALYSIS RESULTS")
    print("=" * 60)
    
    # Print dimensions
    if has_reference:
        print(f"\nDimensions (px): {dimensions['length_px']} x {dimensions['width_px']}")
        print(f"Dimensions (mm): {dimensions['length_mm']:.2f} mm x {dimensions['width_mm']:.2f} mm")
    else:
        print(f"\nDimensions (px): {dimensions['length_px']} x {dimensions['width_px']}")
        print("Dimensions (mm): Not available (no reference provided)")
    
    print(f"Aspect ratio: {dimensions['aspect_ratio']:.2f}")
    
    # Print pin counts
    print("\nPin Count:")
    print(f"  top: {pin_counts['top']}")
    print(f"  right: {pin_counts['right']}")
    print(f"  bottom: {pin_counts['bottom']}")
    print(f"  left: {pin_counts['left']}")
    print(f"  total: {pin_counts['total']}")
    
    print("\n" + "=" * 60)


def main():
    """
    Main pipeline for IC chip physical analysis.
    
    Loads image, preprocesses, detects boundaries, estimates dimensions,
    counts pins, and outputs results.
    """
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description='IC Chip Physical Analysis using Computer Vision',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Basic analysis (pixel dimensions only)
    python ic_physical_analysis.py chip.jpg
    
    # With reference for mm conversion
    python ic_physical_analysis.py chip.jpg --reference-pixels 500 --reference-mm 10
        """
    )
    
    parser.add_argument('image_path', type=str, help='Path to IC chip image')
    parser.add_argument('--reference-pixels', type=float, default=None,
                       help='Reference length in pixels for calibration')
    parser.add_argument('--reference-mm', type=float, default=None,
                       help='Reference length in mm for calibration')
    parser.add_argument('--strip-width', type=int, default=30,
                       help='Width of strip to extract for pin detection (default: 30)')
    parser.add_argument('--min-distance', type=int, default=20,
                       help='Minimum distance between pins in pixels (default: 20)')
    
    args = parser.parse_args()
    
    # Validate input
    if not os.path.exists(args.image_path):
        print(f"Error: Image file not found: {args.image_path}", file=sys.stderr)
        sys.exit(1)
    
    if (args.reference_pixels is None) != (args.reference_mm is None):
        print("Error: Both --reference-pixels and --reference-mm must be provided together",
              file=sys.stderr)
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("IC CHIP PHYSICAL ANALYSIS")
    print("=" * 60)
    print(f"Input image: {args.image_path}\n")
    
    try:
        # Step 1: Load image
        print("[1/5] Loading image...")
        img = cv2.imread(args.image_path)
        
        if img is None:
            raise ValueError(f"Failed to load image: {args.image_path}")
        
        print(f"      Image size: {img.shape[1]}x{img.shape[0]} pixels")
        
        # Step 2: Preprocess
        print("[2/5] Preprocessing image...")
        processed = preprocess_for_ic_analysis(img)
        cv2.imwrite("preprocessed_edges.jpg", processed)
        print("      ✓ Saved: preprocessed_edges.jpg")
        
        # Step 3: Detect IC boundary
        print("[3/5] Detecting IC chip boundary...")
        boundary = detect_ic_boundary(processed, img)
        
        # Step 4: Compute dimensions
        print("[4/5] Computing dimensions...")
        has_reference = args.reference_pixels is not None
        
        dimensions = compute_dimensions_mm(
            boundary['width_pixels'],
            boundary['height_pixels'],
            args.reference_pixels,
            args.reference_mm
        )
        
        # Add pixel dimensions to output
        dimensions['length_px'] = boundary['width_pixels']
        dimensions['width_px'] = boundary['height_pixels']
        
        # Step 5: Count pins
        print("[5/5] Counting pins on all sides...")
        print(f"      Using strip_width={args.strip_width}, min_distance={args.min_distance}")
        
        # Convert original image to grayscale for pin detection
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Apply some preprocessing to help pin detection
        gray = cv2.GaussianBlur(gray, (3, 3), 0)
        
        pin_counts = count_pins(gray, boundary['box'], 
                               strip_width=args.strip_width,
                               min_distance=args.min_distance)
        
        # Print results
        print_results(dimensions, pin_counts, has_reference)
        
        print("\nDebug images saved:")
        print("  - ic_boundary.jpg (IC chip boundary detection)")
        print("  - preprocessed_edges.jpg (edge detection result)")
        print("  - pins_top.jpg (top side pin detection)")
        print("  - pins_right.jpg (right side pin detection)")
        print("  - pins_bottom.jpg (bottom side pin detection)")
        print("  - pins_left.jpg (left side pin detection)")
        
        print("\n" + "=" * 60)
        print("IMPORTANT NOTE:")
        print("=" * 60)
        print("Pin counting uses classical computer vision which may not be")
        print("100% accurate. Check the debug images (pins_*.jpg) to verify")
        print("the detection quality.")
        print("\nTo adjust detection:")
        print(f"  --strip-width {args.strip_width}  (try 20-50)")
        print(f"  --min-distance {args.min_distance}  (try 10-30)")
        print("\n" + "=" * 60)
        print("Analysis complete!")
        print("=" * 60 + "\n")
        
    except Exception as e:
        print(f"\nError during analysis: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
