#!/usr/bin/env python3
"""
Batch Process IC Chip Images

Process multiple IC chip images and generate a comprehensive report.
"""

import os
import sys
import glob
from pathlib import Path
from paddleocr import PaddleOCR
import cv2

def process_image_with_ocr(image_path, ocr, target_heights=[640, 800, 1024]):
    """
    Try processing image with different target heights to find best results.
    
    Args:
        image_path: Path to image
        ocr: PaddleOCR instance
        target_heights: List of heights to try
    
    Returns:
        Best results and the height used
    """
    best_results = []
    best_height = target_heights[0]
    max_detections = 0
    
    for height in target_heights:
        # Load and preprocess
        img = cv2.imread(image_path)
        if img is None:
            continue
        
        # Simple resize
        h, w = img.shape[:2]
        aspect_ratio = w / h
        new_width = int(height * aspect_ratio)
        resized = cv2.resize(img, (new_width, height), interpolation=cv2.INTER_CUBIC)
        
        # Run OCR
        try:
            result = ocr.predict(resized)
            if result and len(result) > 0:
                result_dict = result[0]
                rec_texts = result_dict.get('rec_texts', [])
                rec_scores = result_dict.get('rec_scores', [])
                
                if len(rec_texts) > max_detections:
                    max_detections = len(rec_texts)
                    best_results = list(zip(rec_texts, rec_scores))
                    best_height = height
        except:
            continue
    
    return best_results, best_height


def main():
    """Process all images in the images directory."""
    
    # Initialize OCR once
    print("Initializing PaddleOCR...")
    ocr = PaddleOCR(use_textline_orientation=True, lang='en')
    print("OCR initialized!\n")
    
    # Find all images
    images_dir = "images"
    if not os.path.exists(images_dir):
        print(f"Error: {images_dir} directory not found")
        return
    
    image_files = glob.glob(os.path.join(images_dir, "*.jpeg")) + \
                  glob.glob(os.path.join(images_dir, "*.jpg")) + \
                  glob.glob(os.path.join(images_dir, "*.png"))
    
    if not image_files:
        print(f"No images found in {images_dir}")
        return
    
    print(f"Found {len(image_files)} images to process\n")
    print("="*80)
    
    # Process each image
    results_summary = []
    
    for idx, image_path in enumerate(sorted(image_files), 1):
        filename = os.path.basename(image_path)
        print(f"\n[{idx}/{len(image_files)}] Processing: {filename}")
        print("-"*80)
        
        # Get image info
        img = cv2.imread(image_path)
        if img is None:
            print(f"  ❌ Failed to load image")
            continue
        
        h, w = img.shape[:2]
        print(f"  Original size: {w}x{h}")
        
        # Process with OCR
        results, best_height = process_image_with_ocr(image_path, ocr)
        
        if results:
            print(f"  ✅ Detected {len(results)} text regions (best at height={best_height})")
            for text, score in results:
                confidence_color = "🟢" if score > 0.9 else "🟡" if score > 0.7 else "🔴"
                print(f"     {confidence_color} {text:20s} ({score:.2%})")
            
            results_summary.append({
                'filename': filename,
                'size': f"{w}x{h}",
                'detections': len(results),
                'best_height': best_height,
                'texts': [text for text, _ in results],
                'avg_confidence': sum(score for _, score in results) / len(results)
            })
        else:
            print(f"  ⚠️  No text detected")
            results_summary.append({
                'filename': filename,
                'size': f"{w}x{h}",
                'detections': 0,
                'best_height': None,
                'texts': [],
                'avg_confidence': 0
            })
    
    # Print summary report
    print("\n" + "="*80)
    print("BATCH PROCESSING SUMMARY")
    print("="*80)
    print(f"\nTotal images processed: {len(image_files)}")
    
    successful = sum(1 for r in results_summary if r['detections'] > 0)
    print(f"Successfully detected text: {successful}/{len(image_files)} ({successful/len(image_files)*100:.1f}%)")
    
    total_detections = sum(r['detections'] for r in results_summary)
    print(f"Total text regions detected: {total_detections}")
    
    if successful > 0:
        avg_conf = sum(r['avg_confidence'] for r in results_summary if r['detections'] > 0) / successful
        print(f"Average confidence: {avg_conf:.2%}")
    
    print("\n" + "-"*80)
    print("DETAILED RESULTS")
    print("-"*80)
    
    for r in results_summary:
        status = "✅" if r['detections'] > 0 else "❌"
        print(f"\n{status} {r['filename']}")
        print(f"   Size: {r['size']}, Detections: {r['detections']}", end="")
        if r['best_height']:
            print(f", Best height: {r['best_height']}", end="")
        if r['avg_confidence'] > 0:
            print(f", Avg confidence: {r['avg_confidence']:.2%}")
        else:
            print()
        
        if r['texts']:
            print(f"   Texts: {', '.join(r['texts'])}")
    
    print("\n" + "="*80)
    print("Processing complete!")
    print("="*80)


if __name__ == "__main__":
    main()
