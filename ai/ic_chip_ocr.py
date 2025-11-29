#!/usr/bin/env python3
"""
IC Chip OCR with Preprocessing Pipeline
========================================

This script performs comprehensive image preprocessing and OCR detection
on IC chip images using PaddleOCR.

Dependencies:
    - opencv-python
    - numpy
    - Pillow
    - paddleocr

Usage:
    python ic_chip_ocr.py <path_to_image>

Author: Auto-generated for SIH Project
Date: 2025-11-29
"""

import sys
import os
import argparse
from typing import Tuple, List, Dict, Any
import numpy as np
import cv2
from PIL import Image
from paddleocr import PaddleOCR


def preprocess_image(image_path: str, target_height: int = 640) -> Tuple[np.ndarray, np.ndarray]:
    """
    Apply comprehensive preprocessing pipeline to the input image.
    
    This function performs the following operations:
    1. Load image
    2. Convert to grayscale
    3. Denoise using bilateral filter
    4. Improve contrast using CLAHE
    5. Deskew/auto-rotate using contour angle detection
    6. Auto-crop ROI based on edge detection
    7. Resize to fixed height while maintaining aspect ratio
    
    Args:
        image_path (str): Path to the input image file
        target_height (int): Target height for the output image (default: 640px)
    
    Returns:
        Tuple[np.ndarray, np.ndarray]: (preprocessed grayscale image, preprocessed BGR image) as numpy arrays
    
    Raises:
        FileNotFoundError: If the image file doesn't exist
        ValueError: If the image cannot be loaded
    """
    # Check if file exists
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image file not found: {image_path}")
    
    # Load image using OpenCV
    print(f"[1/7] Loading image: {image_path}")
    image = cv2.imread(image_path)
    
    if image is None:
        raise ValueError(f"Failed to load image: {image_path}")
    
    # Keep a copy of the original color image
    image_bgr = image.copy()
    
    print(f"      Original size: {image.shape[1]}x{image.shape[0]}")
    
    # Convert to grayscale
    print("[2/7] Converting to grayscale...")
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Denoise using bilateral filter (preserves edges while smoothing)
    print("[3/7] Applying bilateral filter for denoising...")
    denoised = cv2.bilateralFilter(gray, d=9, sigmaColor=75, sigmaSpace=75)
    
    # Improve contrast using CLAHE (Contrast Limited Adaptive Histogram Equalization)
    print("[4/7] Enhancing contrast with CLAHE...")
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    contrast_enhanced = clahe.apply(denoised)
    
    # Deskew / Auto-rotate using largest contour angle
    print("[5/7] Detecting skew angle and rotating...")
    deskewed = deskew_image(contrast_enhanced)
    
    # Also apply the same rotation to the color image
    if len(image_bgr.shape) == 3:
        # Get rotation parameters
        binary = cv2.adaptiveThreshold(
            contrast_enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2
        )
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if contours:
            largest_contour = max(contours, key=cv2.contourArea)
            rect = cv2.minAreaRect(largest_contour)
            angle = rect[2]
            if angle < -45:
                angle = 90 + angle
            elif angle > 45:
                angle = angle - 90
            
            if abs(angle) > 0.5:
                (h, w) = image_bgr.shape[:2]
                center = (w // 2, h // 2)
                M = cv2.getRotationMatrix2D(center, angle, 1.0)
                image_bgr = cv2.warpAffine(
                    image_bgr, M, (w, h), 
                    flags=cv2.INTER_CUBIC, 
                    borderMode=cv2.BORDER_REPLICATE
                )
    
    # Auto-crop ROI based on edge detection
    print("[6/7] Auto-cropping ROI...")
    cropped = auto_crop_roi(deskewed)
    
    # If cropping resulted in a very small image, use the deskewed image instead
    if cropped.shape[0] < 100 or cropped.shape[1] < 100:
        print("      Warning: Cropped image too small, using full deskewed image")
        cropped = deskewed
    else:
        # Apply the same crop to the BGR image
        # Get crop coordinates by comparing shapes
        if deskewed.shape != cropped.shape:
            edges = cv2.Canny(deskewed, 50, 150)
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if contours:
                largest_contour = max(contours, key=cv2.contourArea)
                x, y, w, h = cv2.boundingRect(largest_contour)
                margin = 10
                img_h, img_w = image_bgr.shape[:2]
                x = max(0, x - margin)
                y = max(0, y - margin)
                w = min(img_w - x, w + 2 * margin)
                h = min(img_h - y, h + 2 * margin)
                image_bgr = image_bgr[y:y+h, x:x+w]
    
    # Resize to fixed height while maintaining aspect ratio
    print(f"[7/7] Resizing to height {target_height}px...")
    resized = resize_image(cropped, target_height)
    resized_bgr = resize_image(image_bgr, target_height)
    
    print(f"      Final size: {resized.shape[1]}x{resized.shape[0]}")
    
    return resized, resized_bgr


def deskew_image(image: np.ndarray) -> np.ndarray:
    """
    Detect and correct skew in the image using contour detection.
    
    Args:
        image (np.ndarray): Input grayscale image
    
    Returns:
        np.ndarray: Deskewed image
    """
    # Create a binary image using adaptive thresholding
    binary = cv2.adaptiveThreshold(
        image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2
    )
    
    # Find contours
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if not contours:
        print("      No contours found, skipping deskew")
        return image
    
    # Find the largest contour
    largest_contour = max(contours, key=cv2.contourArea)
    
    # Get minimum area rectangle
    rect = cv2.minAreaRect(largest_contour)
    angle = rect[2]
    
    # Adjust angle
    if angle < -45:
        angle = 90 + angle
    elif angle > 45:
        angle = angle - 90
    
    # Only rotate if angle is significant (> 0.5 degrees)
    if abs(angle) > 0.5:
        print(f"      Detected skew angle: {angle:.2f}°")
        
        # Get image center and rotation matrix
        (h, w) = image.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        
        # Perform rotation
        rotated = cv2.warpAffine(
            image, M, (w, h), 
            flags=cv2.INTER_CUBIC, 
            borderMode=cv2.BORDER_REPLICATE
        )
        return rotated
    else:
        print(f"      Skew angle negligible: {angle:.2f}°")
        return image


def auto_crop_roi(image: np.ndarray, margin: int = 10) -> np.ndarray:
    """
    Automatically crop the region of interest using edge detection.
    
    Args:
        image (np.ndarray): Input grayscale image
        margin (int): Margin to add around detected ROI (default: 10px)
    
    Returns:
        np.ndarray: Cropped image
    """
    # Apply Canny edge detection
    edges = cv2.Canny(image, 50, 150)
    
    # Find contours
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if not contours:
        print("      No edges detected, skipping auto-crop")
        return image
    
    # Find the largest contour
    largest_contour = max(contours, key=cv2.contourArea)
    
    # Get bounding rectangle
    x, y, w, h = cv2.boundingRect(largest_contour)
    
    # Add margin and ensure within image bounds
    img_h, img_w = image.shape[:2]
    x = max(0, x - margin)
    y = max(0, y - margin)
    w = min(img_w - x, w + 2 * margin)
    h = min(img_h - y, h + 2 * margin)
    
    # Crop the image
    cropped = image[y:y+h, x:x+w]
    
    print(f"      Cropped from ({x}, {y}) to ({x+w}, {y+h})")
    
    return cropped


def resize_image(image: np.ndarray, target_height: int) -> np.ndarray:
    """
    Resize image to target height while maintaining aspect ratio.
    
    Args:
        image (np.ndarray): Input image
        target_height (int): Target height in pixels
    
    Returns:
        np.ndarray: Resized image
    """
    h, w = image.shape[:2]
    
    # Calculate aspect ratio
    aspect_ratio = w / h
    
    # Calculate new dimensions
    new_height = target_height
    new_width = int(target_height * aspect_ratio)
    
    # Resize image
    resized = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
    
    return resized


def run_ocr(image: np.ndarray, lang: str = 'en') -> List[Tuple[List[List[int]], Tuple[str, float]]]:
    """
    Run PaddleOCR on the preprocessed image.
    
    Args:
        image (np.ndarray): Preprocessed image (grayscale or color)
        lang (str): Language for OCR (default: 'en')
    
    Returns:
        List of tuples containing:
            - Bounding box coordinates
            - Tuple of (detected text, confidence score)
    
    Raises:
        RuntimeError: If OCR initialization or execution fails
    """
    try:
        print("\n" + "="*70)
        print("Initializing PaddleOCR...")
        print("="*70)
        
        # Initialize PaddleOCR
        # Note: use_angle_cls is deprecated, use use_textline_orientation instead
        ocr = PaddleOCR(
            use_textline_orientation=True,  # Enable angle classification (replaces use_angle_cls)
            lang=lang                        # Language
        )
        
        print("Running OCR detection and recognition...")
        
        # Convert grayscale to BGR if needed (PaddleOCR expects BGR)
        if len(image.shape) == 2:
            image_bgr = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        else:
            image_bgr = image
        
        # Run OCR
        result = ocr.predict(image_bgr)
        
        # Handle the new API response format
        if result is None or len(result) == 0:
            print("\nNo text detected in the image.")
            return []
        
        # Extract OCR results - new API returns list with dict containing 'rec_texts', 'rec_scores', and 'dt_polys' or 'rec_polys'
        ocr_results = []
        result_dict = result[0]  # Get first (and usually only) page result
        
        rec_texts = result_dict.get('rec_texts', [])
        rec_scores = result_dict.get('rec_scores', [])
        dt_polys = result_dict.get('dt_polys', result_dict.get('rec_polys', []))
        
        for i in range(len(rec_texts)):
            text = rec_texts[i]
            score = rec_scores[i] if i < len(rec_scores) else 0.0
            bbox = dt_polys[i].tolist() if i < len(dt_polys) else [[0, 0], [0, 0], [0, 0], [0, 0]]
            ocr_results.append((bbox, (text, score)))
        
        return ocr_results
    
    except Exception as e:
        raise RuntimeError(f"OCR execution failed: {str(e)}")


def print_ocr_results(results: List[Tuple[List[List[int]], Tuple[str, float]]]) -> None:
    """
    Pretty-print OCR results with formatting.
    
    Args:
        results: OCR results from PaddleOCR
    """
    print("\n" + "="*70)
    print("OCR RESULTS")
    print("="*70)
    
    if not results:
        print("No text detected.")
        return
    
    print(f"\nTotal text regions detected: {len(results)}\n")
    
    for idx, item in enumerate(results, 1):
        bbox = item[0]
        text_info = item[1]
        text = text_info[0]
        confidence = text_info[1]
        
        print(f"[{idx}] Text: {text}")
        print(f"    Confidence: {confidence:.4f} ({confidence*100:.2f}%)")
        
        # Format bounding box coordinates
        bbox_flat = [coord for point in bbox for coord in point]
        print(f"    BBox: {bbox_flat}")
        print(f"    Coordinates: [(x1, y1), (x2, y2), (x3, y3), (x4, y4)]")
        for i, point in enumerate(bbox, 1):
            print(f"              Point {i}: ({int(point[0])}, {int(point[1])})")
        print()
    
    print("="*70)


def save_preprocessed_image(image: np.ndarray, output_path: str = "preprocessed.jpg") -> None:
    """
    Save the preprocessed image to disk.
    
    Args:
        image (np.ndarray): Preprocessed image
        output_path (str): Output file path
    """
    try:
        cv2.imwrite(output_path, image)
        print(f"\nPreprocessed image saved to: {output_path}")
    except Exception as e:
        print(f"\nWarning: Failed to save preprocessed image: {str(e)}")


def main():
    """
    Main script workflow.
    """
    # Set up argument parser
    parser = argparse.ArgumentParser(
        description='IC Chip OCR with Preprocessing Pipeline',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python ic_chip_ocr.py chip_image.jpg
    python ic_chip_ocr.py path/to/ic_chip.png
        """
    )
    
    parser.add_argument(
        'image_path',
        type=str,
        help='Path to the input IC chip image'
    )
    
    parser.add_argument(
        '--height',
        type=int,
        default=640,
        help='Target height for resized image (default: 640)'
    )
    
    parser.add_argument(
        '--lang',
        type=str,
        default='en',
        help='OCR language (default: en)'
    )
    
    parser.add_argument(
        '--output',
        type=str,
        default='preprocessed.jpg',
        help='Output path for preprocessed image (default: preprocessed.jpg)'
    )
    
    # Parse arguments
    args = parser.parse_args()
    
    print("\n" + "="*70)
    print("IC CHIP OCR WITH PREPROCESSING PIPELINE")
    print("="*70)
    print(f"Input Image: {args.image_path}")
    print(f"Target Height: {args.height}px")
    print(f"OCR Language: {args.lang}")
    print("="*70 + "\n")
    
    try:
        # Step 1: Preprocess the image
        print("STEP 1: PREPROCESSING")
        print("-" * 70)
        preprocessed_gray, preprocessed_bgr = preprocess_image(args.image_path, target_height=args.height)
        
        # Step 2: Save preprocessed image
        print("\nSTEP 2: SAVING PREPROCESSED IMAGE")
        print("-" * 70)
        save_preprocessed_image(preprocessed_gray, args.output)
        
        # Step 3: Run OCR
        print("\nSTEP 3: RUNNING OCR")
        print("-" * 70)
        ocr_results = run_ocr(preprocessed_bgr, lang=args.lang)
        
        # Step 4: Print results
        print_ocr_results(ocr_results)
        
        print("\n" + "="*70)
        print("PROCESSING COMPLETE")
        print("="*70 + "\n")
        
    except FileNotFoundError as e:
        print(f"\nError: {str(e)}")
        sys.exit(1)
    
    except ValueError as e:
        print(f"\nError: {str(e)}")
        sys.exit(1)
    
    except RuntimeError as e:
        print(f"\nError: {str(e)}")
        sys.exit(1)
    
    except Exception as e:
        print(f"\nUnexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
