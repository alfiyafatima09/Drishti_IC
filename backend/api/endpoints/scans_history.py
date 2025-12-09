"""Scan History endpoints - Audit trail operations."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
from datetime import datetime
from uuid import UUID
import logging
import json

from core.database import get_db
from services import ScanService, ICService
from models import ScanHistory
from schemas import (
    ScanListResult,
    ScanListItem,
    ScanDetails,
    ScanStatus,
    ActionRequired,
)
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/scans", tags=["Scan History"])


class ScanHistoryStats(BaseModel):
    """Statistics about scan history."""
    total_scans: int
    pass_count: int
    fail_count: int
    unknown_count: int
    counterfeit_count: int
    partial_count: int
    manual_override_count: int
    with_bottom_scan_count: int
    avg_confidence_score: Optional[float] = None
    unique_manufacturers: int
    unique_batches: int


class EnrichedScanListResult(BaseModel):
    """Scan list result with additional statistics."""
    scans: list[ScanListItem]
    total_count: int
    limit: int
    offset: int
    stats: ScanHistoryStats


class TimeSeriesDataPoint(BaseModel):
    """Data point for time series."""
    date: str
    pass_count: int
    fail_count: int
    unknown_count: int
    counterfeit_count: int
    total: int


class ManufacturerStats(BaseModel):
    """Statistics per manufacturer."""
    manufacturer: str
    count: int
    pass_count: int
    fail_count: int
    pass_rate: float


class BatchStats(BaseModel):
    """Statistics per batch."""
    batch_id: str
    batch_vender: Optional[str]
    count: int
    pass_count: int
    fail_count: int
    pass_rate: float


class AnalyticsResponse(BaseModel):
    """Comprehensive analytics response."""
    summary: ScanHistoryStats
    time_series: list[TimeSeriesDataPoint]
    top_manufacturers: list[ManufacturerStats]
    recent_batches: list[BatchStats]
    confidence_distribution: dict[str, int]  # Range brackets
    hourly_activity: dict[int, int]  # Hour -> count


@router.get("/list", response_model=ScanListResult)
async def list_scans(
    status: Optional[str] = Query(None, description="Filter by status"),
    action_required: Optional[str] = Query(None, description="Filter by required action"),
    part_number: Optional[str] = Query(None, description="Partial match on part number"),
    manufacturer: Optional[str] = Query(None, description="Detected manufacturer"),
    has_bottom_scan: Optional[bool] = Query(None, description="Whether bottom scan exists"),
    manual_override: Optional[bool] = Query(None, description="Whether manual override occurred"),
    batch_id: Optional[str] = Query(None, description="Production batch id"),
    batch_vender: Optional[str] = Query(None, description="Batch vendor"),
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
    if action_required and action_required not in [a.value for a in ActionRequired]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid action_required. Must be one of: {[a.value for a in ActionRequired]}"
        )
    
    scans, total_count = await ScanService.list_scans(
        db=db,
        status=status,
        action_required=action_required,
        part_number=part_number,
        manufacturer=manufacturer,
        has_bottom_scan=has_bottom_scan,
        manual_override=manual_override,
        batch_id=batch_id,
        batch_vender=batch_vender,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )
    
    def parse_json_field(value):
        """Parse JSON field if it's a string, otherwise return as-is."""
        if value is None:
            return None
        if isinstance(value, str):
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return None
        return value
    
    return ScanListResult(
        scans=[
            ScanListItem(
                scan_id=scan.scan_id,
                part_number=scan.part_number_verified or scan.part_number_detected,
                part_number_detected=scan.part_number_detected,
                part_number_candidates=parse_json_field(scan.part_number_candidates),
                part_number_verified=scan.part_number_verified,
                status=ScanStatus(scan.status),
                action_required=ActionRequired(scan.action_required) if scan.action_required else ActionRequired.NONE,
                confidence_score=scan.confidence_score,
                detected_pins=scan.detected_pins,
                expected_pins=scan.expected_pins,
                has_bottom_scan=scan.has_bottom_scan,
                was_manual_override=scan.was_manual_override,
                manufacturer_detected=scan.manufacturer_detected,
                message=scan.message,
                scanned_at=scan.scanned_at,
                completed_at=scan.completed_at,
                batch_id=scan.batch_id,
                batch_vender=scan.batch_vender,
            )
            for scan in scans
        ],
        total_count=total_count,
        limit=limit,
        offset=offset,
    )


@router.get("/list/enriched", response_model=EnrichedScanListResult)
async def list_scans_enriched(
    status: Optional[str] = Query(None, description="Filter by status"),
    action_required: Optional[str] = Query(None, description="Filter by required action"),
    part_number: Optional[str] = Query(None, description="Partial match on part number"),
    manufacturer: Optional[str] = Query(None, description="Detected manufacturer"),
    has_bottom_scan: Optional[bool] = Query(None, description="Whether bottom scan exists"),
    manual_override: Optional[bool] = Query(None, description="Whether manual override occurred"),
    batch_id: Optional[str] = Query(None, description="Production batch id"),
    batch_vender: Optional[str] = Query(None, description="Batch vendor"),
    date_from: Optional[datetime] = Query(None, description="Start date"),
    date_to: Optional[datetime] = Query(None, description="End date"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """
    List all scans with enriched statistics.
    
    This endpoint returns the same scan list as /list but with additional
    statistics about the entire scan history.
    """
    # Get scans using existing service
    scans, total_count = await ScanService.list_scans(
        db=db,
        status=status,
        action_required=action_required,
        part_number=part_number,
        manufacturer=manufacturer,
        has_bottom_scan=has_bottom_scan,
        manual_override=manual_override,
        batch_id=batch_id,
        batch_vender=batch_vender,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )
    
    # Calculate statistics
    pass_count_result = await db.execute(
        select(func.count()).select_from(ScanHistory).where(ScanHistory.status == 'PASS')
    )
    fail_count_result = await db.execute(
        select(func.count()).select_from(ScanHistory).where(ScanHistory.status == 'FAIL')
    )
    unknown_count_result = await db.execute(
        select(func.count()).select_from(ScanHistory).where(ScanHistory.status == 'UNKNOWN')
    )
    counterfeit_count_result = await db.execute(
        select(func.count()).select_from(ScanHistory).where(ScanHistory.status == 'COUNTERFEIT')
    )
    partial_count_result = await db.execute(
        select(func.count()).select_from(ScanHistory).where(ScanHistory.status == 'PARTIAL')
    )
    manual_override_result = await db.execute(
        select(func.count()).select_from(ScanHistory).where(ScanHistory.was_manual_override == True)
    )
    bottom_scan_result = await db.execute(
        select(func.count()).select_from(ScanHistory).where(ScanHistory.has_bottom_scan == True)
    )
    avg_confidence_result = await db.execute(
        select(func.avg(ScanHistory.confidence_score)).select_from(ScanHistory)
    )
    unique_manufacturers_result = await db.execute(
        select(func.count(func.distinct(ScanHistory.manufacturer_detected))).select_from(ScanHistory)
    )
    unique_batches_result = await db.execute(
        select(func.count(func.distinct(ScanHistory.batch_id))).select_from(ScanHistory).where(ScanHistory.batch_id.isnot(None))
    )
    
    stats = ScanHistoryStats(
        total_scans=total_count,
        pass_count=pass_count_result.scalar() or 0,
        fail_count=fail_count_result.scalar() or 0,
        unknown_count=unknown_count_result.scalar() or 0,
        counterfeit_count=counterfeit_count_result.scalar() or 0,
        partial_count=partial_count_result.scalar() or 0,
        manual_override_count=manual_override_result.scalar() or 0,
        with_bottom_scan_count=bottom_scan_result.scalar() or 0,
        avg_confidence_score=avg_confidence_result.scalar(),
        unique_manufacturers=unique_manufacturers_result.scalar() or 0,
        unique_batches=unique_batches_result.scalar() or 0,
    )
    
    def parse_json_field(value):
        """Parse JSON field if it's a string, otherwise return as-is."""
        if value is None:
            return None
        if isinstance(value, str):
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return None
        return value
    
    return EnrichedScanListResult(
        scans=[
            ScanListItem(
                scan_id=scan.scan_id,
                part_number=scan.part_number_verified or scan.part_number_detected,
                part_number_detected=scan.part_number_detected,
                part_number_candidates=parse_json_field(scan.part_number_candidates),
                part_number_verified=scan.part_number_verified,
                status=ScanStatus(scan.status),
                action_required=ActionRequired(scan.action_required) if scan.action_required else ActionRequired.NONE,
                confidence_score=scan.confidence_score,
                detected_pins=scan.detected_pins,
                expected_pins=scan.expected_pins,
                has_bottom_scan=scan.has_bottom_scan,
                was_manual_override=scan.was_manual_override,
                manufacturer_detected=scan.manufacturer_detected,
                message=scan.message,
                scanned_at=scan.scanned_at,
                completed_at=scan.completed_at,
                batch_id=scan.batch_id,
                batch_vender=scan.batch_vender,
            )
            for scan in scans
        ],
        total_count=total_count,
        limit=limit,
        offset=offset,
        stats=stats,
    )


@router.get("/analytics", response_model=AnalyticsResponse)
async def get_scan_analytics(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get comprehensive scan analytics.
    
    Returns time series data, manufacturer stats, batch stats, and more.
    """
    from datetime import timedelta
    from collections import defaultdict
    
    # Calculate date range
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    # Get all scans in date range
    result = await db.execute(
        select(ScanHistory).where(
            ScanHistory.scanned_at >= start_date
        ).order_by(ScanHistory.scanned_at)
    )
    scans = result.scalars().all()
    
    # Calculate summary stats
    total_scans = len(scans)
    pass_count = sum(1 for s in scans if s.status == 'PASS')
    fail_count = sum(1 for s in scans if s.status == 'FAIL')
    unknown_count = sum(1 for s in scans if s.status == 'UNKNOWN')
    counterfeit_count = sum(1 for s in scans if s.status == 'COUNTERFEIT')
    partial_count = sum(1 for s in scans if s.status == 'PARTIAL')
    manual_override_count = sum(1 for s in scans if s.was_manual_override)
    bottom_scan_count = sum(1 for s in scans if s.has_bottom_scan)
    
    # Calculate average confidence
    valid_confidences = [s.confidence_score for s in scans if s.confidence_score is not None]
    avg_confidence = sum(valid_confidences) / len(valid_confidences) if valid_confidences else None
    
    # Count unique manufacturers and batches
    unique_manufacturers = len(set(s.manufacturer_detected for s in scans if s.manufacturer_detected))
    unique_batches = len(set(s.batch_id for s in scans if s.batch_id))
    
    summary = ScanHistoryStats(
        total_scans=total_scans,
        pass_count=pass_count,
        fail_count=fail_count,
        unknown_count=unknown_count,
        counterfeit_count=counterfeit_count,
        partial_count=partial_count,
        manual_override_count=manual_override_count,
        with_bottom_scan_count=bottom_scan_count,
        avg_confidence_score=avg_confidence,
        unique_manufacturers=unique_manufacturers,
        unique_batches=unique_batches,
    )
    
    # Time series data (daily)
    daily_data = defaultdict(lambda: defaultdict(int))
    for scan in scans:
        if scan.scanned_at:
            date_key = scan.scanned_at.date().isoformat()
            daily_data[date_key][scan.status] += 1
            daily_data[date_key]['total'] += 1
    
    time_series = [
        TimeSeriesDataPoint(
            date=date,
            pass_count=data.get('PASS', 0),
            fail_count=data.get('FAIL', 0),
            unknown_count=data.get('UNKNOWN', 0),
            counterfeit_count=data.get('COUNTERFEIT', 0),
            total=data.get('total', 0)
        )
        for date, data in sorted(daily_data.items())
    ]
    
    # Manufacturer stats
    mfg_data = defaultdict(lambda: defaultdict(int))
    for scan in scans:
        if scan.manufacturer_detected:
            mfg = scan.manufacturer_detected
            mfg_data[mfg]['total'] += 1
            if scan.status == 'PASS':
                mfg_data[mfg]['pass'] += 1
            elif scan.status == 'FAIL':
                mfg_data[mfg]['fail'] += 1
    
    top_manufacturers = [
        ManufacturerStats(
            manufacturer=mfg,
            count=data['total'],
            pass_count=data['pass'],
            fail_count=data['fail'],
            pass_rate=round((data['pass'] / data['total'] * 100) if data['total'] > 0 else 0, 1)
        )
        for mfg, data in sorted(mfg_data.items(), key=lambda x: x[1]['total'], reverse=True)[:10]
    ]
    
    # Batch stats
    batch_data = {}
    for scan in scans:
        if scan.batch_id:
            batch = scan.batch_id
            if batch not in batch_data:
                batch_data[batch] = {'total': 0, 'pass': 0, 'fail': 0, 'vender': scan.batch_vender}
            batch_data[batch]['total'] += 1
            if scan.status == 'PASS':
                batch_data[batch]['pass'] += 1
            elif scan.status == 'FAIL':
                batch_data[batch]['fail'] += 1
    
    recent_batches = [
        BatchStats(
            batch_id=batch,
            batch_vender=data['vender'],
            count=data['total'],
            pass_count=data['pass'],
            fail_count=data['fail'],
            pass_rate=round((data['pass'] / data['total'] * 100) if data['total'] > 0 else 0, 1)
        )
        for batch, data in sorted(batch_data.items(), key=lambda x: x[1]['total'], reverse=True)[:10]
    ]
    
    # Confidence distribution
    confidence_buckets = {'0-20': 0, '20-40': 0, '40-60': 0, '60-80': 0, '80-100': 0}
    for scan in scans:
        if scan.confidence_score is not None:
            if scan.confidence_score < 20:
                confidence_buckets['0-20'] += 1
            elif scan.confidence_score < 40:
                confidence_buckets['20-40'] += 1
            elif scan.confidence_score < 60:
                confidence_buckets['40-60'] += 1
            elif scan.confidence_score < 80:
                confidence_buckets['60-80'] += 1
            else:
                confidence_buckets['80-100'] += 1
    
    # Hourly activity
    hourly = defaultdict(int)
    for scan in scans:
        if scan.scanned_at:
            hour = scan.scanned_at.hour
            hourly[hour] += 1
    
    return AnalyticsResponse(
        summary=summary,
        time_series=time_series,
        top_manufacturers=top_manufacturers,
        recent_batches=recent_batches,
        confidence_distribution=confidence_buckets,
        hourly_activity=dict(hourly)
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
    
    def parse_json_field(value):
        """Parse JSON field if it's a string, otherwise return as-is."""
        if value is None:
            return None
        if isinstance(value, str):
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return None
        return value
    
    return ScanDetails(
        scan_id=scan.scan_id,
        ocr_text_raw=scan.ocr_text_raw,
        part_number_detected=scan.part_number_detected,
        part_number_candidates=parse_json_field(scan.part_number_candidates),
        part_number_verified=scan.part_number_verified,
        status=ScanStatus(scan.status),
        confidence_score=scan.confidence_score,
        detected_pins=scan.detected_pins,
        expected_pins=scan.expected_pins,
        manufacturer_detected=scan.manufacturer_detected,
        batch_id=scan.batch_id,
        batch_vender=scan.batch_vender,
        action_required=ActionRequired(scan.action_required) if scan.action_required else ActionRequired.NONE,
        has_bottom_scan=scan.has_bottom_scan,
        was_manual_override=scan.was_manual_override,
        operator_note=scan.operator_note,
        match_details=parse_json_field(scan.match_details),
        verification_checks=parse_json_field(scan.verification_checks),
        failure_reasons=parse_json_field(scan.failure_reasons),
        message=scan.message,
        scanned_at=scan.scanned_at,
        completed_at=scan.completed_at,
        ic_specification=ic_spec,
    )

