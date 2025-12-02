"""
Example script to test the Gemini IC Analysis API.
Upload IC images and get OCR + pin detection results.
"""
import requests
import json
from pathlib import Path

# Base URL
BASE_URL = "http://localhost:8000"

def analyze_ic_image(image_path: str):
    """
    Upload IC image for analysis.
    
    Args:
        image_path: Path to the IC image file
    """
    url = f"{BASE_URL}/api/v1/scan"
    
    print(f"\n{'='*80}")
    print(f"Analyzing IC Image: {Path(image_path).name}")
    print(f"{'='*80}")
    print(f"POST {url}")
    print(f"Uploading: {image_path}\n")
    
    try:
        # Open and upload the image
        with open(image_path, "rb") as f:
            files = {"file": ("ic_image.jpg", f, "image/jpeg")}
            response = requests.post(url, files=files)
        
        if response.status_code == 200:
            data = response.json()
            
            print("✓ Analysis Successful!\n")
            
            # Display results
            print(f"Analysis ID: {data['analysis_id']}")
            print(f"Processing Time: {data['processing_time_ms']:.2f}ms")
            print(f"Analyzed At: {data['analyzed_at']}\n")
            
            # OCR Results
            print("📝 OCR Text Extraction:")
            print("-" * 80)
            ocr = data['ocr_data']
            print(f"  Part Number: {ocr.get('part_number', 'N/A')}")
            print(f"  Manufacturer: {ocr.get('manufacturer', 'N/A')}")
            print(f"  Date Code: {ocr.get('date_code', 'N/A')}")
            print(f"  Lot Code: {ocr.get('lot_code', 'N/A')}")
            print(f"  OCR Confidence: {ocr.get('confidence_score', 0):.1f}%")
            print(f"\n  Raw Text:")
            for line in ocr.get('raw_text', '').split('\n'):
                if line.strip():
                    print(f"    {line}")
            
            if ocr.get('other_markings'):
                print(f"\n  Other Markings: {', '.join(ocr['other_markings'])}")
            
            # Pin Detection Results
            print(f"\n🔌 Pin Count Detection:")
            print("-" * 80)
            pins = data['pin_data']
            print(f"  Pin Count: {pins.get('pin_count', 'N/A')}")
            print(f"  Package Type: {pins.get('package_type', 'N/A')}")
            print(f"  Pin Layout: {pins.get('pin_layout', 'N/A')}")
            print(f"  Detection Confidence: {pins.get('confidence_score', 0):.1f}%")
            print(f"  Detection Method: {pins.get('detection_method', 'N/A')}")
            
        elif response.status_code == 400:
            error = response.json()
            print("✗ Bad Request")
            print(f"  Error: {error.get('detail', {}).get('error', 'Unknown')}")
            print(f"  Message: {error.get('detail', {}).get('message', 'Unknown error')}")
            
        elif response.status_code == 503:
            error = response.json()
            print("✗ Service Unavailable")
            print(f"  Error: {error.get('detail', {}).get('error', 'Unknown')}")
            print(f"  Message: {error.get('detail', {}).get('message', 'Unknown error')}")
            details = error.get('detail', {}).get('details', {})
            if 'suggestion' in details:
                print(f"  Suggestion: {details['suggestion']}")
            
        else:
            print(f"✗ Error: HTTP {response.status_code}")
            print(json.dumps(response.json(), indent=2))
            
    except FileNotFoundError:
        print(f"✗ File not found: {image_path}")
    except requests.exceptions.ConnectionError:
        print("✗ Connection error. Is the server running?")
        print("  Start with: cd /home/rishi/Desktop/Drishti_IC && uvicorn backend.main:app --reload")
    except Exception as e:
        print(f"✗ Error: {e}")


def check_health():
    """Check API health."""
    url = f"{BASE_URL}/api/v1/health"
    
    print(f"\n{'='*80}")
    print("Health Check")
    print(f"{'='*80}")
    print(f"GET {url}\n")
    
    try:
        response = requests.get(url)
        data = response.json()
        
        print(f"Status: {data.get('status', 'unknown')}")
        print(f"Timestamp: {data.get('timestamp', 'N/A')}")
        
        services = data.get('services', {})
        gemini = services.get('gemini_ai', {})
        print(f"\nGemini AI Service:")
        print(f"  Configured: {gemini.get('configured', False)}")
        print(f"  Status: {gemini.get('status', 'unknown')}")
        
    except requests.exceptions.ConnectionError:
        print("✗ Connection error. Server is not running.")
    except Exception as e:
        print(f"✗ Error: {e}")


if __name__ == "__main__":
    print("=" * 80)
    print("Gemini IC Analysis API - Test Script")
    print("=" * 80)
    
    # Check health first
    check_health()
    
    # Example images to test (update paths as needed)
    test_images = [
        "/home/rishi/Desktop/Drishti_IC/ai/images/WhatsApp Image 2025-11-29 at 13.48.11.jpeg",
        "/home/rishi/Desktop/Drishti_IC/ai/images/WhatsApp Image 2025-11-29 at 13.48.12.jpeg",
        # Add more image paths here
    ]
    
    # Analyze each image
    for image_path in test_images:
        if Path(image_path).exists():
            analyze_ic_image(image_path)
        else:
            print(f"\n⚠️  Skipping {Path(image_path).name} - file not found")
    
    print(f"\n{'='*80}")
    print("Testing Complete!")
    print(f"{'='*80}\n")
