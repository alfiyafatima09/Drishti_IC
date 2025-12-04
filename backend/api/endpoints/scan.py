"""Scan endpoints - Core inspection operations."""
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
import logging
import re

from core.database import get_db
from services import ScanService, ICService, FakeService
from services.ocr import extract_text_from_image, OCRResponse
from schemas import (
    ScanResult,
    ManualOverrideRequest,
    ScanStatus,
    ActionRequired,
    ErrorResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["Core Inspection"])


def extract_part_number_from_ocr(ocr_response: OCRResponse) -> tuple[str | None, float]:
    """
    Extract part number from OCR response.
    
    Returns tuple of (part_number, confidence_score).
    Uses the first detected text as it's typically the most prominent marking.
    """
    if not ocr_response.results:
        return None, 0.0
    
    # Get the first result (most prominent text on chip)
    first_result = ocr_response.results[0]
    part_number = first_result.text.strip()
    
    # Clean up part number - remove common non-part characters
    # Keep alphanumeric, dashes, and common IC naming characters
    part_number = re.sub(r'[^\w\-\/]', '', part_number)
    
    # Calculate average confidence across all results
    avg_confidence = sum(r.confidence for r in ocr_response.results) / len(ocr_response.results)
    # Scale to percentage (0-100)
    confidence_score = avg_confidence * 100
    
    logger.debug(f"Extracted part number: {part_number} with confidence: {confidence_score:.1f}%")
    
    return part_number if part_number else None, confidence_score


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
    
    # ========== OCR Processing ==========
    logger.info(f"Processing scan for file: {file.filename}, size: {len(image_data)} bytes")
    
    # Run OCR on the uploaded image
    logger.debug("Starting OCR extraction...")
    ocr_response = extract_text_from_image(image_data, preprocess=True)
    
    if ocr_response.status == "error":
        logger.error(f"OCR failed: {ocr_response.error}")
        raise HTTPException(
            status_code=500, 
            detail=f"OCR processing failed: {ocr_response.error}"
        )
    
    # Get full OCR text for logging and storage
    ocr_text = ocr_response.full_text
    logger.debug(f"OCR extracted text: {ocr_text}")
    logger.debug(f"OCR results count: {len(ocr_response.results)}")
    for i, result in enumerate(ocr_response.results):
        logger.debug(f"  OCR segment {i+1}: '{result.text}' (confidence: {result.confidence:.2%})")
    
    # Extract part number from OCR text
    part_number, confidence_score = extract_part_number_from_ocr(ocr_response)
    
    if not part_number:
        logger.warning("No part number could be extracted from OCR")
        # Still create a scan but with UNKNOWN status
        part_number = "UNKNOWN"
        confidence_score = 0.0
    
    logger.info(f"Extracted part number: {part_number}, confidence: {confidence_score:.1f}%")
    
    # ========== Database Lookup ==========
    # Check if IC exists in the database (Golden Record)
    ic_spec = await ICService.get_by_part_number(db, part_number)
    if ic_spec:
        logger.info(f"IC found in database: {part_number} - {ic_spec.manufacturer}, {ic_spec.pin_count} pins")
    else:
        logger.info(f"IC not found in database: {part_number}")
    
    # ========== Placeholders for Vision Analysis ==========
    # TODO: Integrate with pin detection service (Gemini Vision or local model)
    detected_pins = 0  # Placeholder - would come from vision analysis
    manufacturer_detected = None  # Placeholder - could be extracted from OCR or vision
    
    # Try to extract manufacturer from OCR text (simple heuristic)
    manufacturer_keywords = ['TEXAS', 'TI', 'STM', 'INTEL', 'MICROCHIP', 'ANALOG', 'MAXIM', 'NXP', 'INFINEON']
    for text_segment in ocr_response.texts:
        upper_text = text_segment.upper()
        for keyword in manufacturer_keywords:
            if keyword in upper_text:
                manufacturer_detected = text_segment
                logger.debug(f"Detected manufacturer from OCR: {manufacturer_detected}")
                break
        if manufacturer_detected:
            break
    
    logger.info(f"Creating scan - part_number: {part_number}, pins: {detected_pins}, manufacturer: {manufacturer_detected}")
    
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

