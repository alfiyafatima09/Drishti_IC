"""
Example script demonstrating the multi-provider datasheet download API.
Supports: STM, Texas Instruments (TI), and more.
"""
import requests
import json

# Base URL of the API
BASE_URL = "http://localhost:8000"

def download_datasheet(manufacturer: str, ic_id: str):
    """Download a datasheet for the given IC ID and manufacturer."""
    url = f"{BASE_URL}/datasheets/download"
    
    payload = {
        "manufacturer": manufacturer,
        "ic_id": ic_id
    }
    
    print(f"\nDownloading {manufacturer} datasheet for IC: {ic_id}")
    print(f"POST {url}")
    print(f"Payload: {json.dumps(payload, indent=2)}\n")
    
    try:
        response = requests.post(url, json=payload)
        
        if response.status_code == 201:
            data = response.json()
            print("✓ Success!")
            print(f"  Manufacturer: {data['manufacturer']}")
            print(f"  IC ID: {data['ic_id']}")
            print(f"  Message: {data['message']}")
            print(f"  File Path: {data['file_path']}")
            print(f"  File Size: {data['file_size_bytes']:,} bytes")
            print(f"  Downloaded At: {data['downloaded_at']}")
        elif response.status_code == 404:
            error = response.json()
            print("✗ Datasheet not found")
            print(f"  {error.get('detail', {}).get('message', 'Unknown error')}")
        elif response.status_code == 400:
            error = response.json()
            print("✗ Bad Request")
            print(f"  {error.get('detail', {}).get('message', 'Unknown error')}")
            if 'supported_manufacturers' in error.get('detail', {}).get('details', {}):
                supported = error['detail']['details']['supported_manufacturers']
                print(f"  Supported: {', '.join(supported)}")
        else:
            print(f"✗ Error: HTTP {response.status_code}")
            print(f"  {response.json()}")
            
    except requests.exceptions.ConnectionError:
        print("✗ Connection error. Is the server running?")
        print("  Start with: cd /home/rishi/Desktop/Drishti_IC && uvicorn backend.main:app --reload")
    except Exception as e:
        print(f"✗ Error: {e}")


def check_datasheet(manufacturer: str, ic_id: str):
    """Check if a datasheet exists locally."""
    url = f"{BASE_URL}/datasheets/check/{manufacturer}/{ic_id}"
    
    print(f"\nChecking if {manufacturer} datasheet exists for IC: {ic_id}")
    print(f"GET {url}\n")
    
    try:
        response = requests.get(url)
        data = response.json()
        
        if data.get("exists"):
            print("✓ Datasheet exists locally")
            print(f"  Manufacturer: {data['manufacturer']}")
            print(f"  IC ID: {data['ic_id']}")
            print(f"  File Path: {data['file_info']['file_path']}")
            print(f"  File Size: {data['file_info']['file_size_bytes']:,} bytes")
        else:
            print("✗ Datasheet not found locally")
            print(f"  {data.get('message')}")
            
    except requests.exceptions.ConnectionError:
        print("✗ Connection error. Is the server running?")
    except Exception as e:
        print(f"✗ Error: {e}")


def get_supported_manufacturers():
    """Get list of supported manufacturers."""
    url = f"{BASE_URL}/datasheets/manufacturers"
    
    print(f"\nGetting supported manufacturers")
    print(f"GET {url}\n")
    
    try:
        response = requests.get(url)
        data = response.json()
        
        print("✓ Supported Manufacturers:")
        print(f"  Total: {data['count']}\n")
        
        for code, info in data['details'].items():
            print(f"  {code} - {info['name']}")
            print(f"    URL Pattern: {info['url_pattern']}")
            print(f"    Examples: {', '.join(info['example_ics'])}\n")
            
    except requests.exceptions.ConnectionError:
        print("✗ Connection error. Is the server running?")
    except Exception as e:
        print(f"✗ Error: {e}")


if __name__ == "__main__":
    print("=" * 80)
    print("Multi-Provider Datasheet Download API Examples")
    print("=" * 80)
    
    # Example 1: Get supported manufacturers
    print("\n" + "=" * 80)
    print("Example 1: Get Supported Manufacturers")
    print("=" * 80)
    get_supported_manufacturers()
    
    # Example 2: Download STM32 datasheet
    print("\n" + "=" * 80)
    print("Example 2: Download STM32L031K6 datasheet")
    print("=" * 80)
    download_datasheet("STM", "stm32l031k6")
    
    # Example 3: Download TI datasheet
    print("\n" + "=" * 80)
    print("Example 3: Download LM358 (Texas Instruments) datasheet")
    print("=" * 80)
    download_datasheet("TI", "lm358")
    
    # Example 4: Download another TI IC
    print("\n" + "=" * 80)
    print("Example 4: Download LM555 (Texas Instruments) datasheet")
    print("=" * 80)
    download_datasheet("TI", "lm555")
    
    # Example 5: Check if STM datasheet exists
    print("\n" + "=" * 80)
    print("Example 5: Check if STM32L031K6 exists locally")
    print("=" * 80)
    check_datasheet("STM", "stm32l031k6")
    
    # Example 6: Check if TI datasheet exists
    print("\n" + "=" * 80)
    print("Example 6: Check if LM358 exists locally")
    print("=" * 80)
    check_datasheet("TI", "lm358")
    
    # Example 7: Try unsupported manufacturer (will fail)
    print("\n" + "=" * 80)
    print("Example 7: Try unsupported manufacturer")
    print("=" * 80)
    download_datasheet("INVALID", "test123")
    
    # Example 8: Try non-existent IC (will fail)
    print("\n" + "=" * 80)
    print("Example 8: Try downloading non-existent IC")
    print("=" * 80)
    download_datasheet("STM", "stm99999invalid")
    
    print("\n" + "=" * 80)
    print("Examples completed!")
    print("=" * 80)
