#!/usr/bin/env python3
"""
Simple IC Chip OCR - Clean Output
==================================

Outputs only the extracted text without preprocessing details.

Usage:
    python simple_ocr.py <path_to_image>
"""

import sys
import os
import argparse
import numpy as np
import cv2
from paddleocr import PaddleOCR


def preprocess_and_ocr(image_path: str, target_height: int = 640, show_confidence: bool = True) -> list:
    """
    Preprocess image and run OCR silently.
    
    Full 7-step preprocessing pipeline:
    1. Grayscale conversion
    2. Bilateral filtering (edge-preserving denoising)
    3. CLAHE (Contrast Limited Adaptive Histogram Equalization)
    4. Deskew (straighten rotated text)
    5. Auto-crop (remove excess borders)
    6. Resize to optimal height
    7. Final bilateral filtering
    
    Args:
        image_path: Path to image
        target_height: Target height for resizing
        show_confidence: Whether to show confidence scores
    
    Returns:
        List of (text, confidence) tuples
    """
    # Load image
    if not os.path.exists(image_path):
        print(f"Error: Image not found: {image_path}", file=sys.stderr)
        return []
    
    image = cv2.imread(image_path)
    if image is None:
        print(f"Error: Failed to load image: {image_path}", file=sys.stderr)
        return []
    
    # === FULL PREPROCESSING PIPELINE ===
    
    # Step 1: Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Step 2: Bilateral filter (preserves edges while reducing noise)
    filtered = cv2.bilateralFilter(gray, d=9, sigmaColor=75, sigmaSpace=75)
    
    # Step 3: CLAHE for better contrast (handles various lighting conditions)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(filtered)
    
    # Step 4: Deskew (detect and correct rotation)
    coords = np.column_stack(np.where(enhanced > 0))
    if len(coords) > 0:
        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle
        
        # Only deskew if angle is significant (more than 2 degrees)
        if abs(angle) > 2.0:
            (h, w) = enhanced.shape[:2]
            center = (w // 2, h // 2)
            M = cv2.getRotationMatrix2D(center, angle, 1.0)
            deskewed = cv2.warpAffine(enhanced, M, (w, h),
                                     flags=cv2.INTER_CUBIC,
                                     borderMode=cv2.BORDER_REPLICATE)
        else:
            deskewed = enhanced
    else:
        deskewed = enhanced
    
    # Step 5: Skip auto-crop for better text detection
    # (aggressive cropping can remove important text)
    cropped = deskewed
    
    # Step 6: Resize to optimal height
    h, w = cropped.shape[:2]
    aspect_ratio = w / h
    new_width = int(target_height * aspect_ratio)
    resized = cv2.resize(cropped, (new_width, target_height), interpolation=cv2.INTER_CUBIC)
    
    # Step 7: Final bilateral filtering
    final = cv2.bilateralFilter(resized, d=5, sigmaColor=50, sigmaSpace=50)
    
    # Convert back to BGR for PaddleOCR
    preprocessed = cv2.cvtColor(final, cv2.COLOR_GRAY2BGR)
    
    # Initialize OCR (suppress output)
    try:
        ocr = PaddleOCR(use_textline_orientation=True, lang='en')
        
        # Try preprocessed image first
        result = ocr.predict(preprocessed)
        
        # Extract text and confidence
        results = []
        if result and len(result) > 0:
            result_dict = result[0]
            rec_texts = result_dict.get('rec_texts', [])
            rec_scores = result_dict.get('rec_scores', [])
            
            for i in range(len(rec_texts)):
                text = rec_texts[i]
                score = rec_scores[i] if i < len(rec_scores) else 0.0
                
                # Filter out empty strings and very low confidence
                if text and text.strip() and score > 0.5:
                    results.append((text, score))
        
        # If no good results, try original image with simple resize
        if len(results) == 0:
            h_orig, w_orig = image.shape[:2]
            aspect_ratio = w_orig / h_orig
            new_width = int(target_height * aspect_ratio)
            resized_orig = cv2.resize(image, (new_width, target_height), interpolation=cv2.INTER_CUBIC)
            
            result_orig = ocr.predict(resized_orig)
            
            if result_orig and len(result_orig) > 0:
                result_dict = result_orig[0]
                rec_texts = result_dict.get('rec_texts', [])
                rec_scores = result_dict.get('rec_scores', [])
                
                for i in range(len(rec_texts)):
                    text = rec_texts[i]
                    score = rec_scores[i] if i < len(rec_scores) else 0.0
                    
                    # Lower threshold for fallback
                    if text and text.strip() and score > 0.3:
                        results.append((text, score))
        
        return results
        return results
        
    except Exception as e:
        print(f"Error during OCR: {str(e)}", file=sys.stderr)
        return []


def main():
    parser = argparse.ArgumentParser(
        description='Simple IC Chip OCR - Clean Output',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python simple_ocr.py image.jpg
    python simple_ocr.py image.jpg --no-confidence
    python simple_ocr.py image.jpg --height 1024
    python simple_ocr.py image.jpg --min-confidence 0.8
        """
    )
    
    parser.add_argument('image_path', type=str, help='Path to the IC chip image')
    parser.add_argument('--height', type=int, default=640, help='Target height (default: 640)')
    parser.add_argument('--no-confidence', action='store_true', help='Hide confidence scores')
    parser.add_argument('--min-confidence', type=float, default=0.5, 
                        help='Minimum confidence threshold (default: 0.5)')
    parser.add_argument('--separator', type=str, default='\n', 
                        help='Separator between results (default: newline)')
    
    args = parser.parse_args()
    
    # Run OCR
    results = preprocess_and_ocr(args.image_path, args.height, not args.no_confidence)
    
    if not results:
        print("No text detected.", file=sys.stderr)
        sys.exit(1)
    
    # Print results
    for text, confidence in results:
        # Filter by minimum confidence
        if confidence < args.min_confidence:
            continue
        
        if args.no_confidence:
            print(text)
        else:
            print(f"{text} ({confidence:.2%})")


if __name__ == "__main__":
    main()
