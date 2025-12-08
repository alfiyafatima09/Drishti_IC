"""Scan endpoints - Core inspection operations (Phase 1 & 2)."""
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from services.llm import LLM
import os
from uuid import UUID
import asyncio
import logging
import re
from pathlib import Path
from typing import Optional
import uuid
from datetime import datetime

from core.database import get_db
from services import ScanService, ICService
from services.ocr import extract_text_from_image
from services.verification_service import VerificationService
from services.llm import LLM
from schemas.scan_verify import (
    ScanExtractResult,
    ScanVerifyRequest,
    ScanVerifyResult,
    ScanStatus,
    ActionRequired,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["Core Inspection"])

# Maximum number of adjacent lines to combine when generating candidates
MAX_ADJACENT_LINES = 4


def clean_text_for_part_number(text: str) -> str:
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
    
    for length in range(1, min(max_adjacent + 1, n + 1)):
        for start in range(n - length + 1):
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
    
    if 4 <= len(candidate) <= 20:
        score += 20
    elif len(candidate) < 4:
        score -= 10
    elif len(candidate) > 20:
        score -= 5
    
    if re.match(r'^[A-Z]{1,4}\d', candidate, re.IGNORECASE):
        score += 30
    
    has_letters = bool(re.search(r'[A-Za-z]', candidate))
    has_numbers = bool(re.search(r'\d', candidate))
    if has_letters and has_numbers:
        score += 25
    
    known_prefixes = ['LM', 'NE', 'TL', 'OP', 'AD', 'MAX', 'TPS', 'LT', 'STM', 'PIC', 
                      'AT', 'MC', 'SN', 'CD', 'HEF', 'ICL', 'UC', 'UCC', 'TDA', 'LF']
    for prefix in known_prefixes:
        if candidate.upper().startswith(prefix):
            score += 15
            break
    
    suffix_patterns = [r'-[A-Z]{1,3}$', r'/[A-Z]+$', r'[A-Z]{1,2}$']
    for pattern in suffix_patterns:
        if re.search(pattern, candidate, re.IGNORECASE):
            score += 5
            break
    
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


def _parse_pin_count(raw_pin_count) -> int:
    """Convert LLM pin count output to int safely."""
    try:
        return int(raw_pin_count)
    except (TypeError, ValueError):
        return 0


@router.post("/scan", response_model=ScanExtractResult)
async def scan_image(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """
    **Phase 1: Extract & Detect**
    
    Upload IC image for OCR text extraction and pin detection via Vision.
    Returns extracted data without database verification.
    
    **Status**:
    - EXTRACTED: Data ready for verification
    - NEED_BOTTOM_SCAN: No pins detected (BTC component - flip and rescan)
    
    **Next Step**: Call `/api/v1/scan/verify` with the scan_id for database comparison.
    """
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    # Read and save image
    image_data = await file.read()
    backend_root = Path(__file__).resolve().parent.parent.parent
    image_dir = backend_root / "scanned_images"
    image_dir.mkdir(parents=True, exist_ok=True)

    suffix = Path(file.filename).suffix if file.filename else ".img"
    image_path = image_dir / f"{uuid.uuid4()}{suffix}"
    await asyncio.to_thread(image_path.write_bytes, image_data)

    logger.info(f"Processing scan for file: {file.filename}, size: {len(image_data)} bytes")
    
    # ========== OCR Processing ==========
    logger.debug("Starting OCR extraction...")
    ocr_response = extract_text_from_image(image_data, preprocess=True)
    print(ocr_response)
    
    if ocr_response.status == "error":
        logger.error(f"OCR failed: {ocr_response.error}")
        raise HTTPException(
            status_code=500, 
            detail=f"OCR processing failed: {ocr_response.error}"
        )
    
    # Get OCR text and calculate confidence
    ocr_text = ocr_response.full_text
    logger.debug(f"OCR extracted text: {ocr_text}")
    logger.debug(f"OCR results count: {len(ocr_response.results)}")
    for i, result in enumerate(ocr_response.results):
        logger.debug(f"  OCR segment {i+1}: '{result.text}' (confidence: {result.confidence:.2%})")
    
    avg_confidence = 0.0
    if ocr_response.results:
        avg_confidence = sum(r.confidence for r in ocr_response.results) / len(ocr_response.results) * 100
    
    # ========== Generate Part Number Candidates ==========
    # Normalize OCR lines and keep confidence for fallbacks
    ocr_lines = [r.text.strip() for r in ocr_response.results if r.text.strip()]
    cleaned_lines = [clean_text_for_part_number(line) for line in ocr_lines if clean_text_for_part_number(line)]

    candidates = generate_adjacent_combinations(cleaned_lines, MAX_ADJACENT_LINES)
    logger.info(f"Generated {len(candidates)} part number candidates")
    
    # Get best guess from scored candidates
    best_part_number, _ = get_best_guess_part_number(candidates)
    # Fallback: if scoring returned UNKNOWN but we do have OCR lines, pick highest-confidence line
    if (not best_part_number or best_part_number == "UNKNOWN") and ocr_response.results:
        top_result = max(ocr_response.results, key=lambda r: r.confidence)
        fallback_text = clean_text_for_part_number(top_result.text)
        if fallback_text:
            best_part_number = fallback_text
    # ========== Placeholders for Vision Analysis ==========
    # TODO: Integrate with pin detection service (Gemini Vision or local model)
    detected_pins = 0  # Placeholder - would come from vision analysis
    manufacturer_detected = None  # Placeholder - could be extracted from OCR or vision
    
    # ========== Detect Manufacturer ==========
    manufacturer_detected = None
    manufacturer_keywords = ['TEXAS', 'TI', 'STM', 'INTEL', 'MICROCHIP', 'ANALOG', 'MAXIM', 'NXP', 
                            'INFINEON', 'ATMEL', 'FREESCALE', 'ON SEMI', 'ONSEMI', 'FAIRCHILD',
                            'NATIONAL', 'LINEAR', 'VISHAY', 'ROHM', 'TOSHIBA', 'RENESAS']
    for text_segment in ocr_response.texts:
        upper_text = text_segment.upper()
        for keyword in manufacturer_keywords:
            if keyword in upper_text:
                manufacturer_detected = keyword
                break
        if manufacturer_detected:
            break
    
    # Normalize OCR-detected manufacturer to full name
    if manufacturer_detected:
        manufacturer_map = {
            'TI': 'Texas Instruments', 'TEXAS': 'Texas Instruments',
            'STM': 'STMicroelectronics',
            'ATMEL': 'Microchip Technology', 'MICROCHIP': 'Microchip Technology',
            'INTEL': 'Intel Corporation',
            'ANALOG': 'Analog Devices',
            'MAXIM': 'Maxim Integrated',
            'NXP': 'NXP Semiconductors', 'FREESCALE': 'NXP Semiconductors',
            'ON SEMI': 'ON Semiconductor', 'ONSEMI': 'ON Semiconductor', 'FAIRCHILD': 'ON Semiconductor',
            'NATIONAL': 'Texas Instruments',
            'LINEAR': 'Analog Devices',
            'INFINEON': 'Infineon Technologies',
            'VISHAY': 'Vishay Intertechnology',
            'ROHM': 'ROHM Semiconductor',
            'TOSHIBA': 'Toshiba Electronic Devices & Storage Corporation',
            'RENESAS': 'Renesas Electronics'
        }
        manufacturer_detected = manufacturer_map.get(manufacturer_detected.upper(), manufacturer_detected)
    
    # ========== Vision Analysis (LLM) ==========
    detected_pins = 0
    is_vision_fallback = False
    try:
        llm_client = LLM()
        llm_result = llm_client.analyze_image(str(image_path))
        print(str(image_path))
        print(llm_result)
        
        if llm_result.get("_fallback"):
            is_vision_fallback = True
            logger.warning(f"Vision endpoint unavailable: {llm_result.get('_debug_message')}. Using fallback (0 pins).")
        else:
            logger.info(f"Vision analysis successful: {llm_result}")
        
        detected_pins = _parse_pin_count(llm_result.get("pin_count", 0))
        
        # Use LLM manufacturer if available (takes precedence over OCR)
        llm_manufacturer = llm_result.get("manufacturer", "").strip()
        if llm_manufacturer:
            manufacturer_detected = llm_manufacturer
            logger.info(f"Using LLM-detected manufacturer: {manufacturer_detected}")
    except Exception as e:
        is_vision_fallback = True
        logger.warning(f"Vision analysis failed: {e}, using fallback (0 pins)")
        detected_pins = 0
    
    # ========== Determine Status ==========
    # Check if BTC component (no pins detected)
    if detected_pins == 0:
        status = ScanStatus.NEED_BOTTOM_SCAN
        action_required = ActionRequired.SCAN_BOTTOM
        message = "Pins not visible on this side. This may be a bottom-terminated component (QFN, BGA, LGA). Please flip the IC and scan the bottom."
    else:
        status = ScanStatus.EXTRACTED
        action_required = ActionRequired.VERIFY
        message = "Data extracted successfully. Ready for database verification."
    
    # ========== Create Scan Record ==========
    scan = await ScanService.create_extraction_scan(
        db=db,
        ocr_text=ocr_text,
        part_number_detected=best_part_number,
        part_number_candidates=candidates,
        detected_pins=detected_pins,
        confidence_score=avg_confidence,
        manufacturer_detected=manufacturer_detected,
        status=status.value,
    )
    
    logger.info(
        f"Extraction complete - scan_id: {scan.scan_id}, "
        f"part_number: {best_part_number}, pins: {detected_pins}, status: {status}"
    )
    
    return ScanExtractResult(
        scan_id=scan.scan_id,
        status=status,
        action_required=action_required,
        confidence_score=avg_confidence,
        ocr_text=ocr_text,
        part_number_detected=best_part_number,
        part_number_candidates=candidates,
        manufacturer_detected=manufacturer_detected,
        detected_pins=detected_pins,
        message=message,
        scanned_at=scan.scanned_at,
    )



@router.post("/scan/verify", response_model=ScanVerifyResult)
async def verify_ic(
    request: ScanVerifyRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    **Phase 2: Verify & Compare**
    
    Takes extracted data from `/api/v1/scan` and compares against the Golden Record database.
    
    **Input**:
    - `scan_id`: Reference to extraction scan (required)
    - `part_number`: Override detected part number (optional)
    - `detected_pins`: Override detected pins (optional)
    
    **Returns** one of:
    - **MATCH_FOUND**: IC found in database, all checks passed
    - **PIN_MISMATCH**: Part number found but pin count doesn't match
    - **NOT_IN_DATABASE**: Part number not found, added to sync queue
    
    **Reason Field**: Includes detailed failure reason for each failed check.
    """
    # Get the extraction scan
    scan = await ScanService.get_by_scan_id(db, request.scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail=f"Scan {request.scan_id} not found")
    
    logger.info(f"Verifying scan {request.scan_id}")
    
    # Use overrides or fallback to extracted data
    part_number = request.part_number or scan.part_number_detected
    detected_pins = request.detected_pins if request.detected_pins is not None else scan.detected_pins
    
    if not part_number:
        raise HTTPException(status_code=400, detail="No part number available for verification")
    
    # Perform verification
    verify_result, error = await VerificationService.verify_scan(
        db=db,
        scan_id=request.scan_id,
        part_number_override=request.part_number,
        detected_pins_override=request.detected_pins,
    )
    
    if error:
        raise HTTPException(status_code=500, detail=error)
    
    # Set the scan_id in result
    verify_result.scan_id = request.scan_id
    
    logger.info(
        f"Verification complete - status: {verify_result.verification_status}, "
        f"part_number: {part_number}, pins: {detected_pins}"
    )
    
    return verify_result


@router.post("/scan/{scan_id}/bottom", response_model=ScanExtractResult)
async def scan_bottom_image(
    scan_id: UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload bottom-view image for BTC components.
    
    Used when initial scan returns status=NEED_BOTTOM_SCAN.
    Replaces the extracted pins with pins detected from the bottom.
    """
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    # Check if scan exists
    existing_scan = await ScanService.get_by_scan_id(db, scan_id)
    if not existing_scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    if existing_scan.status != ScanStatus.NEED_BOTTOM_SCAN.value:
        raise HTTPException(
            status_code=400,
            detail="This scan does not require a bottom scan"
        )

    # Read and process bottom image
    image_data = await file.read()
    backend_root = Path(__file__).resolve().parent.parent.parent
    image_dir = backend_root / "scanned_images"
    
    suffix = Path(file.filename).suffix if file.filename else ".img"
    image_path = image_dir / f"{uuid.uuid4()}{suffix}"
    await asyncio.to_thread(image_path.write_bytes, image_data)
    
    logger.info(f"Processing bottom scan for scan_id: {scan_id}")
    
    # Vision analysis on bottom image
    detected_pins = 0
    try:
        llm_client = LLM()
        llm_result = await asyncio.to_thread(llm_client.analyze_image, str(image_path))
        
        # Check if fallback mode
        if llm_result.get("_fallback"):
            logger.warning(f"Bottom vision endpoint unavailable: {llm_result.get('_debug_message')}. Using fallback (0 pins).")
        else:
            logger.info(f"Bottom image vision: detected pins = {llm_result.get('pin_count')}")
        
        detected_pins = _parse_pin_count(llm_result.get("pin_count", 0))
        logger.info(f"Bottom image vision: detected {detected_pins} pins")
    except Exception as e:
        logger.warning(f"Bottom vision analysis failed: {e}, using fallback (0 pins)")
        detected_pins = 0
    except Exception as e:
        logger.warning(f"Bottom vision analysis failed: {e}")
        detected_pins = 0
    
    # Update scan with bottom scan results
    scan = await ScanService.update_bottom_scan(
        db=db,
        scan_id=scan_id,
        detected_pins=detected_pins,
    )
    
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    
    logger.info(f"Bottom scan processed - detected {detected_pins} pins")
    
    return ScanExtractResult(
        scan_id=scan.scan_id,
        status=ScanStatus.EXTRACTED,
        action_required=ActionRequired.VERIFY,
        confidence_score=scan.confidence_score,
        ocr_text=scan.ocr_text_raw or "",
        part_number_detected=scan.part_number_detected or "",
        part_number_candidates=scan.part_number_candidates or [],
        manufacturer_detected=scan.manufacturer_detected,
        detected_pins=detected_pins,
        message="Bottom scan complete. Ready for verification.",
        scanned_at=scan.scanned_at,
    )


@router.post("/scan/override", response_model=ScanExtractResult)
async def manual_override(
    request: dict,
    db: AsyncSession = Depends(get_db),
):
    """
    Manual part number correction.
    
    Allows operator to override the OCR-detected part number.
    Returns the corrected extraction data.
    """
    scan_id = UUID(request.get("scan_id"))
    manual_part_number = request.get("manual_part_number")
    operator_note = request.get("operator_note")
    
    if not manual_part_number:
        raise HTTPException(status_code=400, detail="manual_part_number is required")
    
    scan = await ScanService.get_by_scan_id(db, scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    
    logger.info(
        f"Manual override: scan_id={scan_id}, "
        f"detected='{scan.part_number_detected}' -> manual='{manual_part_number}'"
    )
    
    # Update with manual part number
    scan.part_number_detected = manual_part_number
    scan.was_manual_override = True
    scan.operator_note = operator_note
    await db.flush()
    await db.refresh(scan)
    
    return ScanExtractResult(
        scan_id=scan.scan_id,
        status=ScanStatus.EXTRACTED,
        action_required=ActionRequired.VERIFY,
        confidence_score=scan.confidence_score,
        ocr_text=scan.ocr_text_raw or "",
        part_number_detected=manual_part_number,
        part_number_candidates=scan.part_number_candidates or [],
        manufacturer_detected=scan.manufacturer_detected,
        detected_pins=scan.detected_pins,
        message="Part number corrected. Ready for verification.",
        scanned_at=scan.scanned_at,
    )


def _parse_pin_count(raw_pin_count) -> int:
    """Convert LLM pin count output to int safely."""
    try:
        return int(raw_pin_count)
    except (TypeError, ValueError):
        return 0

