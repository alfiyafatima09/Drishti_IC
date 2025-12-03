#!/usr/bin/env python3
"""
Example script demonstrating how to use the image upload API.
"""
import requests
import sys
from pathlib import Path


def upload_image(
    image_path: str,
    api_url: str = "http://localhost:8000",
    denoise: bool = True,
    enhance_contrast: bool = False,
    normalize: bool = True,
    edge_prep: bool = False
):
    """
    Upload an image to the Drishti IC API.
    
    Args:
        image_path: Path to the image file
        api_url: Base URL of the API
        denoise: Apply denoising
        enhance_contrast: Apply contrast enhancement
        normalize: Apply normalization
        edge_prep: Apply edge detection preparation
        
    Returns:
        API response as dictionary
    """
    endpoint = f"{api_url}/images/upload"
    
    # Check if file exists
    file_path = Path(image_path)
    if not file_path.exists():
        raise FileNotFoundError(f"Image file not found: {image_path}")
    
    # Determine content type
    content_type_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".bmp": "image/bmp",
        ".tiff": "image/tiff",
        ".tif": "image/tiff",
        ".heif": "image/heif",
        ".heic": "image/heic"
    }
    
    ext = file_path.suffix.lower()
    content_type = content_type_map.get(ext, "image/jpeg")
    
    # Prepare request
    with open(file_path, "rb") as f:
        files = {
            "file": (file_path.name, f, content_type)
        }
        data = {
            "denoise": str(denoise).lower(),
            "enhance_contrast": str(enhance_contrast).lower(),
            "normalize": str(normalize).lower(),
            "edge_prep": str(edge_prep).lower()
        }
        
        print(f"Uploading {file_path.name}...")
        print(f"  Size: {file_path.stat().st_size / 1024:.1f} KB")
        print(f"  Type: {content_type}")
        print(f"  Preprocessing options:")
        print(f"    - Denoise: {denoise}")
        print(f"    - Enhance contrast: {enhance_contrast}")
        print(f"    - Normalize: {normalize}")
        print(f"    - Edge prep: {edge_prep}")
        print()
        
        try:
            response = requests.post(endpoint, files=files, data=data)
            response.raise_for_status()
            
            result = response.json()
            
            print("✓ Upload successful!")
            print(f"  Image ID: {result['image_id']}")
            print(f"  Stored at: {result['file_path']}")
            print(f"  Preprocessing steps: {', '.join(result['preprocessing']['steps_applied'])}")
            print()
            
            return result
            
        except requests.exceptions.HTTPError as e:
            print(f"✗ Upload failed with status {response.status_code}")
            try:
                error_detail = response.json()
                print(f"  Error: {error_detail.get('detail', 'Unknown error')}")
                if 'error_code' in error_detail:
                    print(f"  Code: {error_detail['error_code']}")
            except:
                print(f"  Response: {response.text}")
            raise
        except requests.exceptions.RequestException as e:
            print(f"✗ Request failed: {e}")
            raise


def main():
    """Main function for command-line usage."""
    if len(sys.argv) < 2:
        print("Usage: python example_upload.py <image_path> [api_url]")
        print()
        print("Example:")
        print("  python example_upload.py ic_chip.jpg")
        print("  python example_upload.py ic_chip.jpg http://localhost:8000")
        sys.exit(1)
    
    image_path = sys.argv[1]
    api_url = sys.argv[2] if len(sys.argv) > 2 else "http://localhost:8000"
    
    try:
        result = upload_image(
            image_path,
            api_url=api_url,
            denoise=True,
            enhance_contrast=False,
            normalize=True,
            edge_prep=False
        )
        
        print("Full response:")
        import json
        print(json.dumps(result, indent=2))
        
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
