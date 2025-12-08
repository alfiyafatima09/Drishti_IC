"""Pydantic schemas for scan operations."""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID

from schemas.common import ScanStatus, ActionRequired, PartNumberSource
from schemas.ic import ICSpecificationResponse


class MatchDetails(BaseModel):
    """Details about what matched during verification."""
    part_number_match: Optional[bool] = None
    pin_count_match: Optional[bool] = None
    manufacturer_match: Optional[bool] = None


class FakeRegistryInfo(BaseModel):
    """Info about fake registry entry."""
    added_at: datetime
    source: str
    reason: Optional[str] = None


class DimensionData(BaseModel):
    """IC chip dimension measurement results."""
    width_mm: float = Field(..., description="IC width in millimeters")
    height_mm: float = Field(..., description="IC height in millimeters")
    area_mm2: float = Field(..., description="IC area in square millimeters")
    confidence: str = Field(..., description="Detection confidence (high/medium/low)")


class ScanResult(BaseModel):
    """Complete scan result response."""
    scan_id: UUID
    status: ScanStatus
    action_required: ActionRequired = ActionRequired.NONE
    confidence_score: Optional[float] = Field(None, ge=0, le=100)
    ocr_text: Optional[str] = None
    image_path: Optional[str] = None
    part_number: Optional[str] = None
    part_number_candidates: Optional[list[str]] = None 
    part_number_source: PartNumberSource = PartNumberSource.OCR_BEST_GUESS 
    manufacturer_detected: Optional[str] = None
    detected_pins: Optional[int] = None
    dimension_data: Optional[DimensionData] = None
    message: Optional[str] = None
    match_details: Optional[MatchDetails] = None
    queued_for_sync: bool = False
    queued_candidates_count: int = 0  # How many candidates were queued
    ic_specification: Optional[ICSpecificationResponse] = None
    fake_registry_info: Optional[FakeRegistryInfo] = None
    was_manual_override: bool = False
    scanned_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ManualOverrideRequest(BaseModel):
    """Request to manually override a scan's part number."""
    scan_id: UUID
    manual_part_number: str
    operator_note: Optional[str] = None


class ScanListItem(BaseModel):
    """Abbreviated scan info for list responses."""
    scan_id: UUID
    part_number: Optional[str] = None
    status: ScanStatus
    confidence_score: Optional[float] = None
    detected_pins: Optional[int] = None
    scanned_at: datetime

    class Config:
        from_attributes = True


class ScanListResult(BaseModel):
    """Paginated list of scans."""
    scans: list[ScanListItem]
    total_count: int
    limit: int
    offset: int


class ScanDetails(BaseModel):
    """Full scan details response."""
    scan_id: UUID
    ocr_text_raw: Optional[str] = None
    part_number_detected: Optional[str] = None
    part_number_verified: Optional[str] = None
    status: ScanStatus
    confidence_score: Optional[float] = None
    detected_pins: Optional[int] = None
    expected_pins: Optional[int] = None
    manufacturer_detected: Optional[str] = None
    action_required: ActionRequired = ActionRequired.NONE
    has_bottom_scan: bool = False
    was_manual_override: bool = False
    match_details: Optional[MatchDetails] = None
    failure_reasons: Optional[list[str]] = None
    message: Optional[str] = None
    scanned_at: datetime
    completed_at: Optional[datetime] = None
    ic_specification: Optional[ICSpecificationResponse] = None

    class Config:
        from_attributes = True

