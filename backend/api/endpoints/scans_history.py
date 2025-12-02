"""Scan History endpoints - Audit trail operations."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from datetime import datetime
from uuid import UUID
import logging

from core.database import get_db
from services import ScanService, ICService
from schemas import (
    ScanListResult,
    ScanListItem,
    ScanDetails,
    ScanStatus,
    ActionRequired,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/scans", tags=["Scan History"])


@router.get("/list", response_model=ScanListResult)
async def list_scans(
    status: Optional[str] = Query(None, description="Filter by status"),
    date_from: Optional[datetime] = Query(None, description="Start date"),
    date_to: Optional[datetime] = Query(None, description="End date"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """
    List all scans with optional filters.
    """
    # Validate status if provided
    if status and status not in [s.value for s in ScanStatus]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {[s.value for s in ScanStatus]}"
        )
    
    scans, total_count = await ScanService.list_scans(
        db=db,
        status=status,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )
    
    return ScanListResult(
        scans=[
            ScanListItem(
                scan_id=scan.scan_id,
                part_number=scan.part_number_verified or scan.part_number_detected,
                status=ScanStatus(scan.status),
                confidence_score=scan.confidence_score,
                detected_pins=scan.detected_pins,
                scanned_at=scan.scanned_at,
            )
            for scan in scans
        ],
        total_count=total_count,
        limit=limit,
        offset=offset,
    )


@router.get("/{scan_id}/details", response_model=ScanDetails)
async def get_scan_details(
    scan_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Get full details of a specific scan.
    """
    scan = await ScanService.get_by_scan_id(db, scan_id)
    
    if not scan:
        raise HTTPException(
            status_code=404,
            detail={"error": "SCAN_NOT_FOUND", "message": "Scan not found"}
        )
    
    # Get IC specification if available
    ic_spec = None
    part_number = scan.part_number_verified or scan.part_number_detected
    if part_number:
        ic_spec_model = await ICService.get_by_part_number(db, part_number)
        if ic_spec_model:
            ic_spec = ic_spec_model.to_dict()
    
    return ScanDetails(
        scan_id=scan.scan_id,
        ocr_text_raw=scan.ocr_text_raw,
        part_number_detected=scan.part_number_detected,
        part_number_verified=scan.part_number_verified,
        status=ScanStatus(scan.status),
        confidence_score=scan.confidence_score,
        detected_pins=scan.detected_pins,
        expected_pins=scan.expected_pins,
        manufacturer_detected=scan.manufacturer_detected,
        action_required=ActionRequired(scan.action_required) if scan.action_required else ActionRequired.NONE,
        has_bottom_scan=scan.has_bottom_scan,
        was_manual_override=scan.was_manual_override,
        match_details=scan.match_details,
        failure_reasons=scan.failure_reasons,
        message=scan.message,
        scanned_at=scan.scanned_at,
        completed_at=scan.completed_at,
        ic_specification=ic_spec,
    )

