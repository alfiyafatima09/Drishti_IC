import sys
import os
import cv2
import numpy as np

# Add backend directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.dimension_service import DimensionService

def debug_run():
    image_path = "/home/knk/.gemini/antigravity/brain/02294369-74b5-456c-bdf3-e9964398234e/uploaded_image_1765197869893.jpg"
    
    if not os.path.exists(image_path):
        print(f"Error: Image not found at {image_path}")
        return

    print(f"Debugging image: {image_path}")
    
    # 1. Measure using current logic
    print("\n--- Running Measure ---")
    result = DimensionService.measure_from_path(image_path)
    
    if result:
        print("\n--- Result ---")
        print(f"Width: {result['width_mm']} mm ({result['width_px']} px)")
        print(f"Height: {result['height_mm']} mm ({result['height_px']} px)")
        print(f"MM per Pixel: {result['mm_per_pixel']}")
        print(f"Confidence: {result['confidence']}")
    else:
        print("Measurement failed.")

    # 2. Try the unused pin detection method directly
    print("\n--- Testing Pin Detection Method (Unused) ---")
    image = cv2.imread(image_path)
    from dimensions.ic_dimension_measurement import preprocess_image, detect_ic_body
    
    preprocessed = preprocess_image(image)
    ic_contour, rotated_rect = detect_ic_body(preprocessed, image)
    
    if ic_contour is not None:
        mm_per_pixel_pins = DimensionService._detect_pins_and_calculate_pitch(image, ic_contour)
        if mm_per_pixel_pins:
            print(f"SUCCESS! Pin detection calculated mm_per_pixel: {mm_per_pixel_pins}")
            print(f"Would result in Width: {result['width_px'] * mm_per_pixel_pins:.2f} mm")
            print(f"Would result in Height: {result['height_px'] * mm_per_pixel_pins:.2f} mm")
        else:
            print("Pin detection returned None")
    else:
        print("Could not detect IC contour for pin test")

if __name__ == "__main__":
    debug_run()
