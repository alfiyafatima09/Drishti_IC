"""Scan endpoints - Core inspection operations."""
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from services.llm import LLM
import os
from uuid import UUID
import logging
import re
from typing import Optional

from core.database import get_db
from services import ScanService, ICService, FakeService, QueueService
from services.ocr import extract_text_from_image, OCRResponse
from schemas import (
    ScanResult,
    ManualOverrideRequest,
    ScanStatus,
    ActionRequired,
    PartNumberSource,
    ErrorResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["Core Inspection"])
llm_client = LLM()
# Maximum number of adjacent lines to combine when generating candidates
MAX_ADJACENT_LINES = 4


def clean_text_for_part_number(text: str) -> str:
    """Clean text for use as part number candidate."""
    # Remove common non-part characters, keep alphanumeric, dashes, slashes
    return re.sub(r'[^\w\-\/]', '', text.strip())


def generate_adjacent_combinations(lines: list[str], max_adjacent: int = MAX_ADJACENT_LINES) -> list[str]:
    """
    Generate all adjacent line combinations from OCR text lines.
    
    For lines: ["ATMEL", "MEGA32U4", "-AU", "1035E"]
    Generates:
      - Single: ["ATMEL", "MEGA32U4", "-AU", "1035E"]
      - Pairs: ["ATMELMEGA32U4", "MEGA32U4-AU", "-AU1035E"]
      - Triples: ["ATMELMEGA32U4-AU", "MEGA32U4-AU1035E"]
      - etc. up to max_adjacent
    
    Returns unique candidates ordered by combination length (shorter first).
    """
    if not lines:
        return []
    
    candidates = []
    n = len(lines)
    
    # Generate combinations of 1 to max_adjacent adjacent lines
    for length in range(1, min(max_adjacent + 1, n + 1)):
        for start in range(n - length + 1):
            # Combine adjacent lines
            combined = "".join(lines[start:start + length])
            cleaned = clean_text_for_part_number(combined)
            if cleaned and cleaned not in candidates:
                candidates.append(cleaned)
    
    logger.debug(f"Generated {len(candidates)} candidates from {n} OCR lines")
    return candidates


def score_ic_pattern(candidate: str) -> float:
    """
    Score a candidate based on how likely it looks like an IC part number.
    Higher score = more likely to be a valid part number.
    
    IC patterns typically:
    - Have letters followed by numbers (LM555, STM32F407)
    - May have suffix like -AU, -P, /DIP
    - Usually 4-20 characters
    - Start with letters (manufacturer prefix)
    """
    score = 0.0
    
    # Length penalty - too short or too long is unlikely
    if 4 <= len(candidate) <= 20:
        score += 20
    elif len(candidate) < 4:
        score -= 10
    elif len(candidate) > 20:
        score -= 5
    
    # Pattern: Letters followed by numbers (common IC naming)
    if re.match(r'^[A-Z]{1,4}\d', candidate, re.IGNORECASE):
        score += 30
    
    # Contains both letters and numbers
    has_letters = bool(re.search(r'[A-Za-z]', candidate))
    has_numbers = bool(re.search(r'\d', candidate))
    if has_letters and has_numbers:
        score += 25
    
    # Known manufacturer prefixes (boost score)
    known_prefixes = ['LM', 'NE', 'TL', 'OP', 'AD', 'MAX', 'TPS', 'LT', 'STM', 'PIC', 
                      'AT', 'MC', 'SN', 'CD', 'HEF', 'ICL', 'UC', 'UCC', 'TDA', 'LF']
    for prefix in known_prefixes:
        if candidate.upper().startswith(prefix):
            score += 15
            break
    
    # Common suffixes (boost score)
    suffix_patterns = [r'-[A-Z]{1,3}$', r'/[A-Z]+$', r'[A-Z]{1,2}$']
    for pattern in suffix_patterns:
        if re.search(pattern, candidate, re.IGNORECASE):
            score += 5
            break
    
    # Penalize pure numbers or pure letters
    if candidate.isdigit():
        score -= 30
    if candidate.isalpha() and len(candidate) < 6:
        score -= 20
    
    return score


def get_best_guess_part_number(candidates: list[str]) -> tuple[str, float]:
    """
    From a list of candidates, pick the one most likely to be the IC part number.
    Returns (best_candidate, score).
    """
    if not candidates:
        return "UNKNOWN", 0.0
    
    scored = [(c, score_ic_pattern(c)) for c in candidates]
    scored.sort(key=lambda x: x[1], reverse=True)
    
    logger.debug("Candidate scores:")
    for candidate, score in scored[:5]:  # Log top 5
        logger.debug(f"  '{candidate}': {score:.1f}")
    
    best = scored[0]
    return best[0], best[1]


@router.post("/scan", response_model=ScanResult)
async def scan_image(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload image for IC inspection.
    
    Performs OCR and Vision analysis, then verifies against Golden Record.
    Returns PASS, FAIL, PARTIAL, UNKNOWN, or COUNTERFEIT.
    
    The endpoint:
    1. Extracts text using OCR
    2. Generates all adjacent line combinations (up to 4 lines)
    3. Checks each candidate against the database
    4. If match found: returns verified part number
    5. If no match: queues ALL candidates and returns best guess
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
    
    # Calculate average OCR confidence
    avg_confidence = 0.0
    if ocr_response.results:
        avg_confidence = sum(r.confidence for r in ocr_response.results) / len(ocr_response.results) * 100
    
    # ========== Generate Part Number Candidates ==========
    # Get individual text lines from OCR
    ocr_lines = [r.text.strip() for r in ocr_response.results if r.text.strip()]
    
    # Generate all adjacent combinations
    candidates = generate_adjacent_combinations(ocr_lines, MAX_ADJACENT_LINES)
    logger.info(f"Generated {len(candidates)} part number candidates from {len(ocr_lines)} OCR lines")
    logger.debug(f"Candidates: {candidates}")
    
    # ========== Database Lookup - Try Each Candidate ==========
    matched_part_number: Optional[str] = None
    matched_ic_spec = None
    part_number_source = PartNumberSource.OCR_BEST_GUESS
    
    for candidate in candidates:
        ic_spec = await ICService.get_by_part_number(db, candidate)
        if ic_spec:
            matched_part_number = candidate
            matched_ic_spec = ic_spec
            part_number_source = PartNumberSource.DATABASE_MATCH
            logger.info(f"DATABASE MATCH FOUND: '{candidate}' - {ic_spec.manufacturer}, {ic_spec.pin_count} pins")
            break
        logger.debug(f"No match for candidate: '{candidate}'")
    
    # ========== Determine Final Part Number ==========
    queued_candidates_count = 0
    
    if matched_part_number:
        # We found a match!
        part_number = matched_part_number
        logger.info(f"Using database-matched part number: {part_number}")
    else:
        # No match - use best guess and queue ALL candidates
        part_number, guess_score = get_best_guess_part_number(candidates)
        logger.info(f"No database match. Best guess: '{part_number}' (score: {guess_score:.1f})")
        
        # Queue ALL candidates for sync
        if candidates:
            logger.info(f"Queueing {len(candidates)} candidates for sync...")
            for candidate in candidates:
                await QueueService.add_to_queue(db, candidate)
                logger.debug(f"  Queued: '{candidate}'")
            queued_candidates_count = len(candidates)
        else:
            # No candidates at all - queue "UNKNOWN"
            await QueueService.add_to_queue(db, "UNKNOWN")
            queued_candidates_count = 1
    
    # ========== Placeholders for Vision Analysis ==========
    # TODO: Integrate with pin detection service (Gemini Vision or local model)
    
    
    llm_result = llm_client.analyze_image(file.path)
    detected_pins = int(llm_result.get("pin_count", 0)) if llm_result.get("pin_count") else 0
    manufacturer_detected = llm_result.get("manufacturer", None)
    
    # Try to extract manufacturer from OCR text (simple heuristic)
    manufacturer_keywords = ['TEXAS', 'TI', 'STM', 'INTEL', 'MICROCHIP', 'ANALOG', 'MAXIM', 'NXP', 
                            'INFINEON', 'ATMEL', 'FREESCALE', 'ON SEMI', 'ONSEMI', 'FAIRCHILD',
                            'NATIONAL', 'LINEAR', 'VISHAY', 'ROHM', 'TOSHIBA', 'RENESAS']
    for text_segment in ocr_response.texts:
        upper_text = text_segment.upper()
        for keyword in manufacturer_keywords:
            if keyword in upper_text:
                manufacturer_detected = text_segment
                logger.debug(f"Detected manufacturer from OCR: {manufacturer_detected}")
                break
        if manufacturer_detected:
            break
    
    logger.info(f"Creating scan - part_number: {part_number}, source: {part_number_source.value}, pins: {detected_pins}")
    
    # Create scan and perform verification
    scan = await ScanService.create_scan(
        db=db,
        ocr_text=ocr_text,
        part_number=part_number,
        detected_pins=detected_pins,
        confidence_score=avg_confidence,
        manufacturer_detected=manufacturer_detected,
    )
    
    # Get IC specification if available
    ic_spec_response = None
    if matched_ic_spec:
        ic_spec_response = matched_ic_spec.to_dict()
    elif scan.status in [ScanStatus.PASS.value, ScanStatus.FAIL.value, ScanStatus.PARTIAL.value]:
        ic_spec_model = await ICService.get_by_part_number(db, part_number)
        if ic_spec_model:
            ic_spec_response = ic_spec_model.to_dict()
    
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
        part_number_candidates=candidates if candidates else None,
        part_number_source=part_number_source,
        manufacturer_detected=scan.manufacturer_detected,
        detected_pins=scan.detected_pins,
        message=scan.message,
        match_details=scan.match_details,
        queued_for_sync=(scan.status == ScanStatus.UNKNOWN.value),
        queued_candidates_count=queued_candidates_count,
        ic_specification=ic_spec_response,
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
        part_number_source=PartNumberSource.DATABASE_MATCH,  # Bottom scan only happens after initial match
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
        part_number_source=PartNumberSource.MANUAL_OVERRIDE,
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

