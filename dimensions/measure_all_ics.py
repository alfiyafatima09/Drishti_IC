"""
Batch IC Dimension Measurement Script
======================================

This script demonstrates how to measure IC dimensions for multiple images
and saves results to a CSV file.
"""

import os
import cv2
import csv
from ic_dimension_measurement import measure_ic_dimensions, print_results

def measure_all_ics_in_folder(folder_path: str, 
                               output_folder: str = "results",
                               mm_per_pixel: float = None,
                               focal_length_mm: float = 3.04,
                               sensor_height_mm: float = 2.74,
                               camera_height_mm: float = 120.0):
    """
    Measure all IC chips in a folder and save results.
    
    Args:
        folder_path: Path to folder containing IC images
        output_folder: Folder to save visualization images and CSV
        mm_per_pixel: Direct scaling factor (optional)
        focal_length_mm: Camera focal length
        sensor_height_mm: Camera sensor height
        camera_height_mm: Camera height above object
    """
    # Create output folder if it doesn't exist
    os.makedirs(output_folder, exist_ok=True)
    
    # Supported image formats
    image_extensions = ('.png', '.jpg', '.jpeg', '.bmp', '.tif', '.tiff')
    
    # Get all image files
    image_files = [f for f in os.listdir(folder_path) 
                   if f.lower().endswith(image_extensions)]
    
    if not image_files:
        print(f"No image files found in {folder_path}")
        return
    
    print(f"\nFound {len(image_files)} images to process\n")
    
    # Prepare CSV output
    csv_path = os.path.join(output_folder, "ic_measurements.csv")
    csv_file = open(csv_path, 'w', newline='')
    csv_writer = csv.writer(csv_file)
    csv_writer.writerow(['Filename', 'Width_mm', 'Height_mm', 'Width_px', 'Height_px', 
                         'Area_mm2', 'mm_per_pixel', 'Angle_deg', 'Status'])
    
    successful = 0
    failed = 0
    
    # Process each image
    for idx, filename in enumerate(sorted(image_files), 1):
        image_path = os.path.join(folder_path, filename)
        print(f"\n[{idx}/{len(image_files)}] Processing: {filename}")
        print("-" * 60)
        
        try:
            # Measure IC dimensions
            results = measure_ic_dimensions(
                image_path=image_path,
                mm_per_pixel=mm_per_pixel,
                focal_length_mm=focal_length_mm,
                sensor_height_mm=sensor_height_mm,
                camera_height_mm=camera_height_mm,
                debug=False
            )
            
            # Print results
            print(f"✓ IC Body Width:  {results['width_mm']:.2f} mm ({results['width_px']:.1f} px)")
            print(f"✓ IC Body Height: {results['height_mm']:.2f} mm ({results['height_px']:.1f} px)")
            print(f"✓ Area:           {results['width_mm'] * results['height_mm']:.2f} mm²")
            
            # Save visualization
            output_filename = f"measured_{os.path.splitext(filename)[0]}.png"
            output_path = os.path.join(output_folder, output_filename)
            cv2.imwrite(output_path, results['visualization'])
            print(f"✓ Saved visualization: {output_filename}")
            
            # Write to CSV
            csv_writer.writerow([
                filename,
                f"{results['width_mm']:.2f}",
                f"{results['height_mm']:.2f}",
                f"{results['width_px']:.1f}",
                f"{results['height_px']:.1f}",
                f"{results['width_mm'] * results['height_mm']:.2f}",
                f"{results['mm_per_pixel']:.6f}",
                f"{results['angle']:.2f}",
                "SUCCESS"
            ])
            
            successful += 1
            
        except Exception as e:
            print(f"✗ Failed to process {filename}: {str(e)}")
            csv_writer.writerow([filename, '', '', '', '', '', '', '', f"FAILED: {str(e)}"])
            failed += 1
    
    csv_file.close()
    
    # Print summary
    print("\n" + "="*60)
    print("BATCH PROCESSING SUMMARY")
    print("="*60)
    print(f"Total images:     {len(image_files)}")
    print(f"Successful:       {successful}")
    print(f"Failed:           {failed}")
    print(f"Results saved to: {output_folder}/")
    print(f"CSV report:       {csv_path}")
    print("="*60 + "\n")


def measure_single_ic_interactive():
    """
    Interactive mode to measure a single IC with custom parameters.
    """
    print("\n" + "="*60)
    print("INTERACTIVE IC DIMENSION MEASUREMENT")
    print("="*60)
    
    # Get image path
    image_path = input("\nEnter image path (or press Enter for default 'images/001.png'): ").strip()
    if not image_path:
        image_path = "images/001.png"
    
    if not os.path.exists(image_path):
        print(f"Error: Image not found at {image_path}")
        return
    
    # Ask for measurement method
    print("\nSelect measurement method:")
    print("  1. Method A: Provide direct mm_per_pixel value")
    print("  2. Method B: Use camera calibration parameters (pinhole model)")
    
    method = input("Enter choice (1 or 2, default=2): ").strip()
    
    mm_per_pixel = None
    focal_length_mm = 3.04
    sensor_height_mm = 2.74
    camera_height_mm = 120.0
    
    if method == "1":
        # Method A: Direct mm_per_pixel
        mm_input = input("\nEnter mm_per_pixel value (e.g., 0.02): ").strip()
        try:
            mm_per_pixel = float(mm_input)
        except ValueError:
            print("Invalid input. Using default camera parameters instead.")
            mm_per_pixel = None
    
    if mm_per_pixel is None:
        # Method B: Camera parameters
        print("\nUsing camera calibration method (pinhole model)")
        print("Current defaults:")
        print(f"  - Focal length:    {focal_length_mm} mm")
        print(f"  - Sensor height:   {sensor_height_mm} mm")
        print(f"  - Camera height:   {camera_height_mm} mm (fixed)")
        
        custom = input("\nUse custom camera parameters? (y/n, default=n): ").strip().lower()
        if custom == 'y':
            try:
                focal_length_mm = float(input("Enter focal length (mm): ").strip())
                sensor_height_mm = float(input("Enter sensor height (mm): ").strip())
            except ValueError:
                print("Invalid input. Using default values.")
    
    # Debug mode
    debug_input = input("\nEnable debug mode? (y/n, default=n): ").strip().lower()
    debug = (debug_input == 'y')
    
    print("\nProcessing...")
    
    try:
        # Measure IC
        results = measure_ic_dimensions(
            image_path=image_path,
            mm_per_pixel=mm_per_pixel,
            focal_length_mm=focal_length_mm,
            sensor_height_mm=sensor_height_mm,
            camera_height_mm=camera_height_mm,
            debug=debug
        )
        
        # Print results
        print_results(results)
        
        # Save visualization
        output_path = "measured_output.png"
        cv2.imwrite(output_path, results['visualization'])
        print(f"Visualization saved to: {output_path}")
        
        # Display
        cv2.imshow("IC Measurement Result", results['visualization'])
        print("\nPress any key to close the window...")
        cv2.waitKey(0)
        cv2.destroyAllWindows()
        
    except Exception as e:
        print(f"\nError: {str(e)}")


if __name__ == "__main__":
    """
    Main entry point with menu options.
    """
    print("\n" + "="*60)
    print("IC DIMENSION MEASUREMENT TOOL")
    print("="*60)
    print("\nSelect mode:")
    print("  1. Batch process all images in folder")
    print("  2. Interactive single image measurement")
    print("  3. Quick test with default settings")
    
    choice = input("\nEnter choice (1, 2, or 3, default=3): ").strip()
    
    if choice == "1":
        # Batch mode
        folder = input("\nEnter folder path (default='images'): ").strip()
        if not folder:
            folder = "images"
        
        output = input("Enter output folder (default='results'): ").strip()
        if not output:
            output = "results"
        
        measure_all_ics_in_folder(
            folder_path=folder,
            output_folder=output,
            mm_per_pixel=None,  # Use camera parameters
            focal_length_mm=3.04,
            sensor_height_mm=2.74,
            camera_height_mm=120.0
        )
    
    elif choice == "2":
        # Interactive mode
        measure_single_ic_interactive()
    
    else:
        # Quick test mode (default)
        print("\nRunning quick test with default settings...")
        print("Testing with: images/001.png")
        
        if os.path.exists("images/001.png"):
            try:
                results = measure_ic_dimensions(
                    image_path="images/001.png",
                    mm_per_pixel=None,
                    focal_length_mm=3.04,
                    sensor_height_mm=2.74,
                    camera_height_mm=120.0,
                    debug=False
                )
                
                print_results(results)
                
                cv2.imwrite("quick_test_result.png", results['visualization'])
                print("Visualization saved to: quick_test_result.png")
                
                cv2.imshow("IC Measurement Result", results['visualization'])
                print("\nPress any key to close the window...")
                cv2.waitKey(0)
                cv2.destroyAllWindows()
                
            except Exception as e:
                print(f"\nError: {str(e)}")
        else:
            print("\nError: images/001.png not found")
            print("Please ensure the images folder exists with test images.")
