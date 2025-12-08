#!/usr/bin/env python3
"""
IC Pin Counting Pipeline

This pipeline:
1. Runs classifier.py on the ORIGINAL image to determine IC package type and which sides have pins
2. Runs moon.py to generate edge-detected images
3. Runs the appropriate pin counting script on the edges image based on classification
4. Returns the estimated total pin count

Usage:
    python pipeline.py <input_image> [--debug_dir <dir>]

Example:
    python pipeline.py ic_test/b7.jpeg --debug_dir square
"""

import argparse
import os
import sys
from pathlib import Path
from typing import Tuple, Dict, Any, List

# Add correct/ folder to path for imports
sys.path.insert(0, str(Path(__file__).parent / "correct"))

# Import from correct/ folder
from correct.moon import count_ic_pins_opencv
from correct.classifier import detect_ic_pins_enhanced


def run_moon(input_image: str, debug_dir: str) -> str:
    """
    Run moon.py to generate edge-detected image.
    
    Returns:
        Path to the generated edges image (e.g., square/b7_07_edges.png)
    """
    print(f"[Pipeline] Running moon.py edge detection...")
    
    result = count_ic_pins_opencv(input_image, debug_dir)
    
    # Determine the edges image path
    base_name = Path(input_image).stem
    edges_path = Path(debug_dir) / f"{base_name}_07_edges.png"
    
    if not edges_path.exists():
        raise FileNotFoundError(f"Expected edges image not found: {edges_path}")
    
    print(f"[Pipeline] Edge detection complete. Pin count from moon.py: {result['pin_count']}")
    return str(edges_path)


def run_classifier(edges_image: str, debug: bool = False) -> Dict[str, Any]:
    """
    Run classifier.py to determine package type and sides with pins.
    
    Returns:
        Classification result dict with:
        - classification: "LQFN", "QFN_SINGLE_SIDE", "QFN_DUAL_SIDE", or "QFN_4_SIDE"
        - sides_with_pins: list like ["top", "bottom"] or ["left", "right"]
        - spike_counts: dict with counts per side
    """
    print(f"[Pipeline] Running classifier on {edges_image}...")
    
    result = detect_ic_pins_enhanced(edges_image, debug=debug)
    
    print(f"[Pipeline] Classification: {result['classification']}")
    print(f"[Pipeline] Sides with pins: {result['sides_with_pins']}")
    print(f"[Pipeline] Detection method: {result['detection_method']}")
    
    return result


def run_count_pins_simple(edges_image: str, debug_dir: str) -> int:
    """
    Run count_pins_simple.py for DIP packages with top/bottom pins.
    Uses symmetry: best side count × 2
    
    Returns:
        Estimated total pin count
    """
    # Import here to avoid circular imports
    from correct.count_pins_simple import count_pins
    
    base_name = Path(edges_image).stem
    output_path = str(Path(debug_dir) / f"{base_name}_pins_simple.png")
    
    print(f"[Pipeline] Running count_pins_simple (top/bottom pins)...")
    estimated_total = count_pins(edges_image, output_path)
    
    return estimated_total


def run_annotate_mask_pins(edges_image: str, debug_dir: str) -> int:
    """
    Run annotate_mask_pins.py for DIP packages with left/right pins.
    Uses symmetry: best side count × 2
    
    Returns:
        Estimated total pin count
    """
    # Import here to avoid circular imports
    from correct.annotate_mask_pins import run, find_pin_centers, count_pins_by_side, side_regularity
    import cv2
    
    base_name = Path(edges_image).stem
    output_path = Path(debug_dir) / f"{base_name}_pins_masked.png"
    
    print(f"[Pipeline] Running annotate_mask_pins (left/right pins)...")
    
    # Load image and process
    img = cv2.imread(edges_image, cv2.IMREAD_COLOR)
    if img is None:
        print(f"[Pipeline] Error: Could not read {edges_image}")
        return 0
    
    pins = find_pin_centers(img, min_area=250.0)
    h, w = img.shape[:2]
    cx, cy = w / 2.0, h / 2.0
    
    # Calculate regularity scores for each side
    sides = ["top", "right", "bottom", "left"]
    side_metrics = {}
    for side in sides:
        cnt, score = side_regularity(pins, side, cx, cy)
        side_metrics[side] = (cnt, score)
    
    # Pick the side with the best regularity score
    best_side = max(sides, key=lambda s: (side_metrics[s][1], side_metrics[s][0]))
    best_count = side_metrics[best_side][0]
    
    # For DIP (2 sides), estimate using 2× best side
    estimated_total = best_count * 2
    
    # Run the full function to save annotated output
    run(Path(edges_image), output_path, mask_ratio=0.55, min_area=250.0)
    
    print(f"[Pipeline] Best side: {best_side} with {best_count} pins")
    print(f"[Pipeline] Estimated total (×2): {estimated_total}")
    
    return estimated_total


def run_count_pins_qfp(edges_image: str, debug_dir: str) -> int:
    """
    Run count_pins.py for QFP packages with pins on all 4 sides.
    
    Returns:
        Estimated total pin count
    """
    # Import here to avoid circular imports
    from correct.count_pins import count_pins
    
    base_name = Path(edges_image).stem
    
    print(f"[Pipeline] Running count_pins (4-side QFP)...")
    
    result = count_pins(Path(edges_image))
    
    # result is a tuple, symmetric_pin_count is at index 8
    # (num_labels, areas, pin_areas, pin_labels, bboxes, pin_bboxes, 
    #  package_bbox, side_counts, symmetric_pin_count, ...)
    symmetric_pin_count = result[8]
    
    print(f"[Pipeline] Symmetric pin count: {symmetric_pin_count}")
    
    return symmetric_pin_count


def run_pipeline(input_image: str, debug_dir: str = "debug", classifier_debug: bool = False) -> int:
    """
    Full pipeline: classifier -> moon.py -> appropriate counting script.
    
    Returns:
        Estimated total pin count
    """
    print(f"\n{'='*60}")
    print(f"IC PIN COUNTING PIPELINE")
    print(f"{'='*60}")
    print(f"Input: {input_image}")
    print(f"Debug dir: {debug_dir}")
    print(f"{'='*60}\n")
    
    # Ensure debug directory exists
    os.makedirs(debug_dir, exist_ok=True)
    
    # Step 1: Classify package type using classifier.py on ORIGINAL image
    print("[Step 1] Classifying IC package type (original image)...")
    classification_result = run_classifier(input_image, debug=classifier_debug)
    
    classification = classification_result['classification']
    sides_with_pins = classification_result['sides_with_pins']
    print(f"[Step 1] Result: {classification} - sides: {sides_with_pins}\n")
    
    # Step 2: Run moon.py to generate edges
    print("[Step 2] Generating edge-detected image...")
    edges_image = run_moon(input_image, debug_dir)
    print(f"[Step 2] Edges image: {edges_image}\n")
    
    # Step 3: Run appropriate counting script based on classification
    print(f"[Step 3] Running pin counting on edges image...")
    
    if classification == "LQFN":
        # LQFN - use count_pins.py
        print("[Pipeline] LQFN detected - using count_pins.py")
        estimated_total = run_annotate_mask_pins(edges_image, debug_dir)
        
    elif classification == "QFN_SINGLE_SIDE":
        # Single side - use count_pins_simple.py
        # print("[Pipeline] QFN_SINGLE_SIDE detected - using count_pins_simple.py")
        # estimated_total = run_count_pins_simple(edges_image, debug_dir)
        # call llm
        pass
            
    elif classification == "QFN_DUAL_SIDE":
        # Dual side - use count_pins_simple.py
        # print("[Pipeline] QFN_DUAL_SIDE detected - using count_pins_simple.py")
        # estimated_total = run_count_pins_simple(edges_image, debug_dir)
        # call llm
        pass

    elif classification == "QFN_4_SIDE":
        # 4-side QFP package - use annotate_mask_pins.py
        print("[Pipeline] QFN_4_SIDE detected - using annotate_mask_pins.py")
        estimated_total = run_annotate_mask_pins(edges_image, debug_dir)
        
    else:
        print(f"[Pipeline] Unknown classification: {classification}")
        estimated_total = 0
    
    # Final result
    print(f"\n{'='*60}")
    print(f"PIPELINE RESULT")
    print(f"{'='*60}")
    print(f"Classification: {classification}")
    print(f"Sides with pins: {sides_with_pins}")
    print(f"Estimated Total Pins: {estimated_total}")
    print(f"{'='*60}\n")
    
    return estimated_total


def main():
    parser = argparse.ArgumentParser(
        description="IC Pin Counting Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python pipeline.py ic_test/b7.jpeg
    python pipeline.py ic_test/b7.jpeg --debug_dir square
    python pipeline.py ic_test/b7.jpeg --debug_dir square --classifier_debug
        """
    )
    parser.add_argument("input_image", type=str, help="Path to input IC chip image")
    parser.add_argument("--debug_dir", type=str, default="debug", help="Directory for debug images")
    parser.add_argument("--classifier_debug", action="store_true", 
                       help="Generate debug images from classifier")
    
    args = parser.parse_args()
    
    if not Path(args.input_image).exists():
        print(f"Error: Input image not found: {args.input_image}")
        sys.exit(1)
    
    estimated_total = run_pipeline(args.input_image, args.debug_dir, args.classifier_debug)
    
    # Exit with 0 for success
    sys.exit(0)


if __name__ == "__main__":
    main()
