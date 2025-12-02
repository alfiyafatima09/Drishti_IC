"""Scan endpoints - Core inspection operations."""
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
import logging

from backend.core.database import get_db
from backend.services import ScanService, ICService, FakeService
from backend.schemas import (
    ScanResult,
    ManualOverrideRequest,
    ScanStatus,
    ActionRequired,
    ErrorResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["Core Inspection"])


@router.post("/scan", response_model=ScanResult)
async def scan_image(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload image for IC inspection.
    
    Performs OCR and Vision analysis, then verifies against Golden Record.
    Returns PASS, FAIL, PARTIAL, UNKNOWN, or COUNTERFEIT.
    """
    # Validate file type
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    # Read image
    image_data = await file.read()
    
    # TODO: Integrate with actual OCR and Vision services
    # For now, simulate OCR/Vision results
    # In production, this would call:
    # - backend.services.ocr.perform_ocr(image_data)
    # - backend.services.vision.count_pins(image_data)
    
    # Placeholder OCR/Vision results (replace with actual implementation)
    ocr_text = "LM555CN"  # Simulated
    part_number = "LM555"  # Simulated - extracted from OCR
    detected_pins = 8  # Simulated
    confidence_score = 94.5  # Simulated
    manufacturer_detected = "Texas Instruments"  # Simulated
    
    # Create scan and perform verification
    scan = await ScanService.create_scan(
        db=db,
        ocr_text=ocr_text,
        part_number=part_number,
        detected_pins=detected_pins,
        confidence_score=confidence_score,
        manufacturer_detected=manufacturer_detected,
    )
    
    # Get IC specification if available
    ic_spec = None
    if scan.status in [ScanStatus.PASS.value, ScanStatus.FAIL.value, ScanStatus.PARTIAL.value]:
        ic_spec_model = await ICService.get_by_part_number(db, part_number)
        if ic_spec_model:
            ic_spec = ic_spec_model.to_dict()
    
    # Get fake registry info if counterfeit
    fake_info = None
    if scan.status == ScanStatus.COUNTERFEIT.value:
        fake_entry = await FakeService.get_by_part_number(db, part_number)
        if fake_entry:
            fake_info = fake_entry.to_info()
    
    return ScanResult(
        scan_id=scan.scan_id,
        status=ScanStatus(scan.status),
        action_required=ActionRequired(scan.action_required),
        confidence_score=scan.confidence_score,
        ocr_text=scan.ocr_text_raw,
        part_number=scan.part_number_verified or scan.part_number_detected,
        manufacturer_detected=scan.manufacturer_detected,
        detected_pins=scan.detected_pins,
        message=scan.message,
        match_details=scan.match_details,
        queued_for_sync=(scan.status == ScanStatus.UNKNOWN.value),
        ic_specification=ic_spec,
        fake_registry_info=fake_info,
        scanned_at=scan.scanned_at,
        completed_at=scan.completed_at,
    )


@router.post("/scan/{scan_id}/bottom", response_model=ScanResult)
async def scan_bottom_image(
    scan_id: UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload bottom-view image for BTC components.
    
    Used when initial scan returns action_required=SCAN_BOTTOM.
    """
    # Validate file type
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    # Check if scan exists
    existing_scan = await ScanService.get_by_scan_id(db, scan_id)
    if not existing_scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    if existing_scan.status != ScanStatus.PARTIAL.value:
        raise HTTPException(
            status_code=400,
            detail="This scan does not require a bottom scan"
        )

    # Read image
    image_data = await file.read()
    
    # TODO: Integrate with actual Vision service for pin counting
    # Simulated pin detection from bottom image
    detected_pins = 32  # Simulated
    
    # Process bottom scan
    scan = await ScanService.process_bottom_scan(
        db=db,
        scan_id=scan_id,
        detected_pins=detected_pins,
    )
    
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    
    # Get IC specification
    ic_spec = None
    if scan.part_number_verified:
        ic_spec_model = await ICService.get_by_part_number(db, scan.part_number_verified)
        if ic_spec_model:
            ic_spec = ic_spec_model.to_dict()
    
    return ScanResult(
        scan_id=scan.scan_id,
        status=ScanStatus(scan.status),
        action_required=ActionRequired(scan.action_required),
        confidence_score=scan.confidence_score,
        ocr_text=scan.ocr_text_raw,
        part_number=scan.part_number_verified,
        manufacturer_detected=scan.manufacturer_detected,
        detected_pins=scan.detected_pins,
        message=scan.message,
        match_details=scan.match_details,
        queued_for_sync=False,
        ic_specification=ic_spec,
        scanned_at=scan.scanned_at,
        completed_at=scan.completed_at,
    )


@router.post("/scan/override", response_model=ScanResult)
async def manual_override(
    request: ManualOverrideRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Manual part number correction.
    
    Used when OCR fails to read the chip correctly.
    System still uses vision to verify pin count.
    """
    scan = await ScanService.manual_override(
        db=db,
        scan_id=request.scan_id,
        manual_part_number=request.manual_part_number,
        operator_note=request.operator_note,
    )
    
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    
    # Get IC specification
    ic_spec = None
    if scan.part_number_verified:
        ic_spec_model = await ICService.get_by_part_number(db, scan.part_number_verified)
        if ic_spec_model:
            ic_spec = ic_spec_model.to_dict()
    
    # Get fake registry info if counterfeit
    fake_info = None
    if scan.status == ScanStatus.COUNTERFEIT.value:
        fake_entry = await FakeService.get_by_part_number(db, scan.part_number_verified)
        if fake_entry:
            fake_info = fake_entry.to_info()
    
    return ScanResult(
        scan_id=scan.scan_id,
        status=ScanStatus(scan.status),
        action_required=ActionRequired(scan.action_required),
        confidence_score=scan.confidence_score,
        ocr_text=scan.ocr_text_raw,
        part_number=scan.part_number_verified,
        manufacturer_detected=scan.manufacturer_detected,
        detected_pins=scan.detected_pins,
        message=scan.message,
        match_details=scan.match_details,
        queued_for_sync=(scan.status == ScanStatus.UNKNOWN.value),
        ic_specification=ic_spec,
        fake_registry_info=fake_info,
        was_manual_override=True,
        scanned_at=scan.scanned_at,
        completed_at=scan.completed_at,
    )

