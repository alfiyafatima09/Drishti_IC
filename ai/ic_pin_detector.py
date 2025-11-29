#!/usr/bin/env python3
"""
IC Chip Pin Detection System
=============================

Multi-method pin detection using:
1. Histogram-based classical CV
2. Template matching
3. YOLO object detection
4. Majority voting fusion

Features:
    - Robust preprocessing pipeline
    - Multiple detection strategies
    - Fusion engine for accuracy
    - CPU-based inference
    - Comprehensive debug outputs

Usage:
    python ic_pin_detector.py <image_path> [--yolo-model <path>]

Author: Auto-generated for SIH Project
Date: 2025-11-29
"""

import sys
import os
import argparse
import numpy as np
import cv2
from typing import Tuple, Dict, List, Optional
from scipy.ndimage import gaussian_filter1d
from scipy.signal import find_peaks
import warnings

# Optional YOLO support
try:
    import onnxruntime as ort
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False
    warnings.warn("onnxruntime not available. YOLO detection will be disabled.")


# =============================================================================
# 1. PREPROCESSING + BOUNDARY DETECTION
# =============================================================================

def preprocess_image(img: np.ndarray) -> np.ndarray:
    """
    Preprocess IC chip image for robust boundary and pin detection.
    
    Pipeline:
        1. Grayscale conversion
        2. CLAHE (Contrast Limited Adaptive Histogram Equalization)
        3. Bilateral filter (edge-preserving denoising)
        4. Canny edge detection
        5. Morphological closing
    
    Args:
        img (np.ndarray): Input BGR image
    
    Returns:
        np.ndarray: Preprocessed edge-detected image
    """
    # Step 1: Grayscale conversion
    if len(img.shape) == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img.copy()
    
    # Step 2: CLAHE for contrast enhancement
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    
    # Step 3: Bilateral filter (preserves edges while reducing noise)
    filtered = cv2.bilateralFilter(enhanced, d=9, sigmaColor=75, sigmaSpace=75)
    
    # Step 4: Canny edge detection
    edges = cv2.Canny(filtered, threshold1=50, threshold2=150)
    
    # Step 5: Morphological closing to connect nearby edges
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=2)
    
    return closed


def detect_ic_boundary(
    img: np.ndarray,
    original_img: np.ndarray
) -> Dict:
    """
    Detect IC chip boundary using contour analysis.
    
    Args:
        img (np.ndarray): Preprocessed edge image
        original_img (np.ndarray): Original BGR image for visualization
    
    Returns:
        dict: Boundary information
            {
                "box_points": array of 4 corner points,
                "width_px": width in pixels,
                "height_px": height in pixels,
                "rotation": rotation angle in degrees,
                "center": (cx, cy) center point,
                "box": ((cx, cy), (w, h), angle) minAreaRect output
            }
    """
    # Find all contours
    contours, _ = cv2.findContours(img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if not contours:
        raise ValueError("No contours found in the image")
    
    # Select the largest contour by area (assumed to be the IC chip)
    largest_contour = max(contours, key=cv2.contourArea)
    
    # Fit minimum area rectangle
    rect = cv2.minAreaRect(largest_contour)
    box_points = cv2.boxPoints(rect)
    box_points = np.intp(box_points)
    
    # Extract parameters
    center, (width, height), angle = rect
    
    # Ensure width > height (swap if needed)
    if height > width:
        width, height = height, width
        angle = angle + 90
    
    # Create debug visualization
    debug_img = original_img.copy()
    cv2.drawContours(debug_img, [box_points], 0, (0, 255, 0), 3)
    
    # Draw center point
    cv2.circle(debug_img, (int(center[0]), int(center[1])), 5, (0, 0, 255), -1)
    
    # Add dimension labels
    cv2.putText(debug_img, f"{int(width)}x{int(height)} px", 
                (int(center[0]) - 60, int(center[1]) - 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
    
    # Save debug image
    cv2.imwrite("debug_ic_boundary.jpg", debug_img)
    
    return {
        "box_points": box_points,
        "width_px": int(width),
        "height_px": int(height),
        "rotation": float(angle),
        "center": center,
        "box": rect
    }


# =============================================================================
# 2. SIDE STRIP EXTRACTION
# =============================================================================

def extract_side_strips(
    img: np.ndarray,
    box_points: np.ndarray,
    boundary_info: Dict,
    strip_width: int = 20
) -> Dict[str, np.ndarray]:
    """
    Extract thin strips from all four sides of the IC chip.
    
    Crops long, thin strips along each edge and rotates them so pins
    appear vertically for consistent processing.
    
    Args:
        img (np.ndarray): Grayscale image
        box_points (np.ndarray): 4 corner points of the bounding box
        boundary_info (dict): Boundary detection results
        strip_width (int): Width of strip to extract in pixels
    
    Returns:
        dict: Strip images for each side
            {
                "top": np.ndarray,
                "right": np.ndarray,
                "bottom": np.ndarray,
                "left": np.ndarray
            }
    """
    center, (w, h), angle = boundary_info["box"]
    
    # Get rotation matrix
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    
    # Rotate the entire image
    rotated = cv2.warpAffine(img, M, (img.shape[1], img.shape[0]),
                             flags=cv2.INTER_LINEAR,
                             borderMode=cv2.BORDER_CONSTANT,
                             borderValue=0)
    
    # Calculate crop regions for each side
    cx, cy = int(center[0]), int(center[1])
    w, h = int(w), int(h)
    
    strips = {}
    
    # Top strip (horizontal, along top edge)
    x1, y1 = cx - w // 2, cy - h // 2 - strip_width
    x2, y2 = cx + w // 2, cy - h // 2 + strip_width
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(rotated.shape[1], x2), min(rotated.shape[0], y2)
    strips["top"] = rotated[y1:y2, x1:x2]
    
    # Bottom strip (horizontal, along bottom edge)
    x1, y1 = cx - w // 2, cy + h // 2 - strip_width
    x2, y2 = cx + w // 2, cy + h // 2 + strip_width
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(rotated.shape[1], x2), min(rotated.shape[0], y2)
    strips["bottom"] = rotated[y1:y2, x1:x2]
    
    # Left strip (vertical, along left edge)
    x1, y1 = cx - w // 2 - strip_width, cy - h // 2
    x2, y2 = cx - w // 2 + strip_width, cy + h // 2
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(rotated.shape[1], x2), min(rotated.shape[0], y2)
    strip_left = rotated[y1:y2, x1:x2]
    # Rotate 90° so pins appear vertically
    strips["left"] = cv2.rotate(strip_left, cv2.ROTATE_90_CLOCKWISE)
    
    # Right strip (vertical, along right edge)
    x1, y1 = cx + w // 2 - strip_width, cy - h // 2
    x2, y2 = cx + w // 2 + strip_width, cy + h // 2
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(rotated.shape[1], x2), min(rotated.shape[0], y2)
    strip_right = rotated[y1:y2, x1:x2]
    # Rotate 90° so pins appear vertically
    strips["right"] = cv2.rotate(strip_right, cv2.ROTATE_90_CLOCKWISE)
    
    # Save debug strips
    for side, strip in strips.items():
        if strip.size > 0:
            cv2.imwrite(f"strip_{side}.jpg", strip)
    
    return strips


# =============================================================================
# 3. CLASSICAL CV PIN COUNTING
# =============================================================================

def count_pins_histogram(strip: np.ndarray) -> int:
    """
    Count pins using histogram projection method.
    
    Pipeline:
        1. Apply binary threshold
        2. Sum intensities along short axis (create 1D projection)
        3. Smooth using Gaussian filter
        4. Use scipy.signal.find_peaks to locate pins
        5. Return count
    
    Args:
        strip (np.ndarray): Strip image (pins should be vertical)
    
    Returns:
        int: Number of pins detected
    """
    if strip.size == 0 or strip.shape[0] < 5 or strip.shape[1] < 5:
        return 0
    
    try:
        # Apply bilateral filter for noise reduction
        filtered = cv2.bilateralFilter(strip, 9, 75, 75)
        
        # Try adaptive thresholding first
        try:
            binary = cv2.adaptiveThreshold(
                filtered, 255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY_INV,
                11, 2
            )
        except:
            # Fallback to Otsu
            _, binary = cv2.threshold(filtered, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        
        # Morphological operations to clean up
        kernel = np.ones((2, 2), np.uint8)
        binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        
        # Determine projection direction based on strip orientation
        # We want to project along the long axis (where pins are arranged)
        if strip.shape[1] > strip.shape[0]:
            # Horizontal strip (top/bottom) - project along width
            projection = np.sum(binary, axis=0)
        else:
            # Vertical strip (left/right) - project along height  
            projection = np.sum(binary, axis=1)
        
        # Normalize
        if projection.max() > 0:
            projection = projection.astype(float) / projection.max()
        else:
            return 0
        
        # Smooth with Gaussian
        projection = gaussian_filter1d(projection, sigma=1.5)
        
        # Find peaks with more lenient parameters
        min_distance = max(3, len(projection) // 40)  # Adaptive distance
        peaks, properties = find_peaks(
            projection,
            height=0.2,  # Lower threshold
            distance=min_distance,
            prominence=0.08,
            width=1
        )
        
        return len(peaks)
    
    except Exception as e:
        warnings.warn(f"Histogram method failed: {str(e)}")
        return 0


def count_pins_template(strip: np.ndarray) -> int:
    """
    Count pins using template matching method.
    
    Pipeline:
        1. Create small vertical-line kernel (pin-like template)
        2. Use cv2.matchTemplate to find matches
        3. Collapse to 1D signal
        4. Find peaks
        5. Return count
    
    Args:
        strip (np.ndarray): Strip image (pins should be vertical)
    
    Returns:
        int: Number of pins detected
    """
    if strip.size == 0 or strip.shape[0] < 5 or strip.shape[1] < 5:
        return 0
    
    try:
        # Preprocess strip
        filtered = cv2.bilateralFilter(strip, 5, 50, 50)
        
        # Try adaptive thresholding
        try:
            binary = cv2.adaptiveThreshold(
                filtered, 255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY_INV,
                11, 2
            )
        except:
            _, binary = cv2.threshold(filtered, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        
        # Determine strip orientation and create appropriate template
        if strip.shape[1] > strip.shape[0]:
            # Horizontal strip (top/bottom) - create vertical pin template
            template_height = min(max(5, int(strip.shape[0] * 0.6)), strip.shape[0] - 2)
            template_width = min(max(3, int(strip.shape[1] * 0.02)), 8)
        else:
            # Vertical strip (left/right) - create horizontal pin template
            template_width = min(max(5, int(strip.shape[1] * 0.6)), strip.shape[1] - 2)
            template_height = min(max(3, int(strip.shape[0] * 0.02)), 8)
        
        # Create bar template
        template = np.zeros((template_height, template_width), dtype=np.uint8)
        if strip.shape[1] > strip.shape[0]:
            # Vertical bar for horizontal strips
            center_w = template_width // 2
            template[:, max(0, center_w - 1):min(template_width, center_w + 2)] = 255
        else:
            # Horizontal bar for vertical strips
            center_h = template_height // 2
            template[max(0, center_h - 1):min(template_height, center_h + 2), :] = 255
        
        # Ensure template is smaller than strip
        if template.shape[0] >= binary.shape[0] or template.shape[1] >= binary.shape[1]:
            # Fallback to histogram method
            return count_pins_histogram(strip)
        
        # Match template
        result = cv2.matchTemplate(binary, template, cv2.TM_CCOEFF_NORMED)
        
        # Project along the direction where pins are arranged
        if strip.shape[1] > strip.shape[0]:
            # Horizontal strip - project along width
            projection = np.max(result, axis=0)
        else:
            # Vertical strip - project along height
            projection = np.max(result, axis=1)
        
        # Normalize
        if projection.max() > projection.min():
            projection = (projection - projection.min()) / (projection.max() - projection.min())
        else:
            return 0
        
        # Smooth
        projection = gaussian_filter1d(projection, sigma=1.0)
        
        # Find peaks with more lenient parameters
        min_distance = max(3, len(projection) // 40)
        peaks, _ = find_peaks(
            projection,
            height=0.2,
            distance=min_distance,
            prominence=0.1
        )
        
        return len(peaks)
    
    except Exception as e:
        warnings.warn(f"Template matching failed: {str(e)}")
        return 0


# =============================================================================
# 4. YOLO-BASED PIN DETECTION
# =============================================================================

def count_pins_yolo(
    strip: np.ndarray,
    model_path: Optional[str] = None
) -> Tuple[int, float]:
    """
    Count pins using YOLO object detection (ONNX).
    
    Args:
        strip (np.ndarray): Strip image (pins should be vertical)
        model_path (str): Path to YOLO ONNX model file
    
    Returns:
        tuple: (pin_count, confidence_score)
            - pin_count: Number of detected pins
            - confidence_score: Average confidence (0-1)
    """
    if not YOLO_AVAILABLE:
        return 0, 0.0
    
    if model_path is None or not os.path.exists(model_path):
        warnings.warn("YOLO model not found. Skipping YOLO detection.")
        return 0, 0.0
    
    if strip.size == 0 or strip.shape[0] < 10 or strip.shape[1] < 10:
        return 0, 0.0
    
    try:
        # Load YOLO model (ONNX)
        session = ort.InferenceSession(
            model_path,
            providers=['CPUExecutionProvider']
        )
        
        # Prepare input (resize to 640x640)
        input_size = 640
        original_h, original_w = strip.shape[:2]
        
        # Convert to BGR if grayscale
        if len(strip.shape) == 2:
            strip_bgr = cv2.cvtColor(strip, cv2.COLOR_GRAY2BGR)
        else:
            strip_bgr = strip
        
        # Resize
        resized = cv2.resize(strip_bgr, (input_size, input_size))
        
        # Normalize and transpose
        input_blob = resized.astype(np.float32) / 255.0
        input_blob = np.transpose(input_blob, (2, 0, 1))  # HWC -> CHW
        input_blob = np.expand_dims(input_blob, axis=0)  # Add batch dimension
        
        # Get input name
        input_name = session.get_inputs()[0].name
        
        # Run inference
        outputs = session.run(None, {input_name: input_blob})
        
        # Process detections (assuming YOLO output format)
        detections = outputs[0]  # Shape: (1, N, 85) or similar
        
        # Extract boxes and scores
        boxes = []
        scores = []
        
        # Simple NMS threshold
        conf_threshold = 0.25
        nms_threshold = 0.45
        
        for detection in detections[0]:
            confidence = detection[4]
            if confidence > conf_threshold:
                # Extract box coordinates
                x_center = detection[0] * original_w / input_size
                y_center = detection[1] * original_h / input_size
                width = detection[2] * original_w / input_size
                height = detection[3] * original_h / input_size
                
                x1 = int(x_center - width / 2)
                y1 = int(y_center - height / 2)
                x2 = int(x_center + width / 2)
                y2 = int(y_center + height / 2)
                
                boxes.append([x1, y1, x2, y2])
                scores.append(float(confidence))
        
        # Apply NMS
        if boxes:
            indices = cv2.dnn.NMSBoxes(boxes, scores, conf_threshold, nms_threshold)
            if len(indices) > 0:
                pin_count = len(indices)
                avg_confidence = np.mean([scores[i] for i in indices.flatten()])
                return pin_count, float(avg_confidence)
        
        return 0, 0.0
    
    except Exception as e:
        warnings.warn(f"YOLO detection failed: {str(e)}")
        return 0, 0.0


# =============================================================================
# 5. FUSION ENGINE (MAJORITY VOTING)
# =============================================================================

def fuse_pin_counts(
    count_hist: int,
    count_template: int,
    count_yolo: int,
    yolo_confidence: float = 0.0
) -> int:
    """
    Fuse pin counts from multiple methods using majority voting.
    
    Strategy:
        - If two methods agree → choose that value
        - If all disagree → choose closest two (median)
        - If YOLO confidence < 0.5 → ignore YOLO
        - If only classical methods available → average them
    
    Args:
        count_hist (int): Histogram method count
        count_template (int): Template matching count
        count_yolo (int): YOLO detection count
        yolo_confidence (float): YOLO confidence score (0-1)
    
    Returns:
        int: Fused pin count
    """
    # Collect valid counts
    counts = []
    
    # Always include classical methods
    if count_hist > 0:
        counts.append(count_hist)
    if count_template > 0:
        counts.append(count_template)
    
    # Include YOLO only if confidence is reasonable
    if count_yolo > 0 and yolo_confidence >= 0.5:
        counts.append(count_yolo)
    
    if not counts:
        return 0
    
    if len(counts) == 1:
        return counts[0]
    
    # Check for majority (two or more agree)
    from collections import Counter
    count_freq = Counter(counts)
    
    # If any value appears more than once, it's the majority
    most_common = count_freq.most_common(1)[0]
    if most_common[1] > 1:
        return most_common[0]
    
    # All disagree - use median of closest two
    counts_sorted = sorted(counts)
    if len(counts_sorted) == 2:
        return int(np.mean(counts_sorted))
    elif len(counts_sorted) >= 3:
        # Take middle two values
        mid = len(counts_sorted) // 2
        return int(np.mean([counts_sorted[mid - 1], counts_sorted[mid]]))
    
    return int(np.median(counts))


# =============================================================================
# 6. MAIN PIPELINE
# =============================================================================

def main():
    """
    Main pipeline for IC chip pin detection.
    
    Orchestrates:
        - Image loading
        - Preprocessing
        - Boundary detection
        - Strip extraction
        - Multi-method pin counting
        - Fusion and reporting
    """
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description='IC Chip Pin Detection System (Multi-Method + Fusion)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Without YOLO
    python ic_pin_detector.py chip.jpg
    
    # With YOLO model
    python ic_pin_detector.py chip.jpg --yolo-model yolo_pins.onnx
    
    # Custom strip width
    python ic_pin_detector.py chip.jpg --strip-width 25
        """
    )
    
    parser.add_argument('image_path', type=str, help='Path to IC chip image')
    parser.add_argument('--yolo-model', type=str, default=None,
                       help='Path to YOLO ONNX model (optional)')
    parser.add_argument('--strip-width', type=int, default=20,
                       help='Width of strip to extract (default: 20)')
    
    args = parser.parse_args()
    
    # Validate input
    if not os.path.exists(args.image_path):
        print(f"Error: Image file not found: {args.image_path}", file=sys.stderr)
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("IC CHIP PIN DETECTION SYSTEM")
    print("=" * 60)
    print(f"Input image: {args.image_path}")
    print(f"Strip width: {args.strip_width}")
    print(f"YOLO model: {args.yolo_model if args.yolo_model else 'Not provided'}")
    print("=" * 60 + "\n")
    
    try:
        # Step 1: Load image
        print("[1/6] Loading image...")
        img = cv2.imread(args.image_path)
        if img is None:
            raise ValueError(f"Failed to load image: {args.image_path}")
        print(f"      Image size: {img.shape[1]}x{img.shape[0]} pixels")
        
        # Step 2: Preprocess
        print("[2/6] Preprocessing image...")
        preprocessed = preprocess_image(img)
        cv2.imwrite("debug_preprocessed.jpg", preprocessed)
        print("      ✓ Saved: debug_preprocessed.jpg")
        
        # Step 3: Detect IC boundary
        print("[3/6] Detecting IC chip boundary...")
        boundary = detect_ic_boundary(preprocessed, img)
        print(f"      Dimensions: {boundary['width_px']}x{boundary['height_px']} px")
        print(f"      Rotation: {boundary['rotation']:.1f}°")
        print("      ✓ Saved: debug_ic_boundary.jpg")
        
        # Step 4: Extract side strips
        print("[4/6] Extracting side strips...")
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        strips = extract_side_strips(gray, boundary["box_points"], boundary, args.strip_width)
        print(f"      ✓ Saved: strip_top.jpg, strip_right.jpg, strip_bottom.jpg, strip_left.jpg")
        
        # Step 5: Count pins on each side
        print("[5/6] Counting pins using multiple methods...")
        
        sides = ['top', 'right', 'bottom', 'left']
        pin_counts = {}
        
        for side in sides:
            strip = strips.get(side)
            if strip is None or strip.size == 0:
                pin_counts[side] = 0
                print(f"      {side}: 0 (empty strip)")
                continue
            
            # Method 1: Histogram
            count_hist = count_pins_histogram(strip)
            
            # Method 2: Template matching
            count_template = count_pins_template(strip)
            
            # Method 3: YOLO (if available)
            count_yolo, yolo_conf = count_pins_yolo(strip, args.yolo_model)
            
            # Fusion
            fused_count = fuse_pin_counts(count_hist, count_template, count_yolo, yolo_conf)
            
            pin_counts[side] = fused_count
            
            print(f"      {side}: hist={count_hist}, template={count_template}, " +
                  f"yolo={count_yolo} (conf={yolo_conf:.2f}) → fused={fused_count}")
        
        # Calculate total
        total_pins = sum(pin_counts.values())
        
        # Step 6: Print results
        print("\n[6/6] Final Results:")
        print("\n" + "=" * 60)
        print("Pin Count:")
        for side in sides:
            print(f"  {side}: {pin_counts[side]}")
        print(f"  total: {total_pins}")
        print("=" * 60)
        
        print("\nDebug images saved:")
        print("  - debug_ic_boundary.jpg (IC chip boundary detection)")
        print("  - debug_preprocessed.jpg (preprocessed edge image)")
        print("  - strip_top.jpg, strip_right.jpg, strip_bottom.jpg, strip_left.jpg")
        
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
