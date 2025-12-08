import sys
import os
import asyncio
import uuid
import requests
from datetime import datetime

# Add backend to path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from core.database import async_session_maker
from models import ScanHistory, ICSpecification
from schemas import ScanStatus, ActionRequired

async def setup_test_data():
    scan_id = uuid.uuid4()
    print(f"Creating test scan: {scan_id}")
    
    async with async_session_maker() as db:
        # Check if IC exists, if not create it
        from sqlalchemy import select
        result = await db.execute(select(ICSpecification).where(ICSpecification.part_number == "LM324N"))
        ic = result.scalar_one_or_none()
        
        if not ic:
            print("Creating test IC Specification for LM324N")
            ic = ICSpecification(
                part_number="LM324N",
                manufacturer="Texas Instruments",
                pin_count=14,
                package_type="DIP",
                description="Quad Operational Amplifier",
                datasheet_url="http://example.com/datasheet.pdf",
                electrical_specs={"vcc_max": "32V"},
                source="manual_test"
            )
            db.add(ic)
            await db.flush()

        scan = ScanHistory(
            scan_id=scan_id,
            ocr_text_raw="LM324N\nTI",
            part_number_detected="LM324N",
            status=ScanStatus.EXTRACTED.value,
            action_required=ActionRequired.VERIFY.value,
            confidence_score=0.95,
            detected_pins=14,
            manufacturer_detected="Texas Instruments",
            scanned_at=datetime.utcnow()
        )
        db.add(scan)
        await db.commit()
    return scan_id

def test_verify_endpoint(scan_id):
    url = "http://127.0.0.1:8000/api/v1/scan/verify"
    payload = {
        "scan_id": str(scan_id),
        "part_number": "LM324N",
        "detected_pins": 14
    }
    
    print(f"Testing {url} with payload: {payload}")
    try:
        resp = requests.post(url, json=payload)
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print("Response JSON:")
            print(data)
            
            # Checks
            checks = data.get("verification_checks", {})
            mfg_match = checks.get("manufacturer_match", {})
            print(f"Manufacturer Match Status: {mfg_match.get('status')}")
            
            if mfg_match.get("status") is True:
                 print("SUCCESS: Manufacturer match is TRUE")
            else:
                 print("FAILURE: Manufacturer match is MISSING or FALSE")
                 
            if data.get("verification_status") == "MATCH_FOUND":
                 print("SUCCESS: Overall status is MATCH_FOUND")
            else:
                 print(f"FAILURE: Overall status is {data.get('verification_status')}")

        else:
            print(f"Error: {resp.text}")
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    scan_id = asyncio.run(setup_test_data())
    test_verify_endpoint(scan_id)
