"""Schemas for scan verification operations."""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from uuid import UUID


class VerificationStatus(str, Enum):
    """Verification result status."""
    MATCH_FOUND = "MATCH_FOUND"
    PIN_MISMATCH = "PIN_MISMATCH"
    MANUFACTURER_MISMATCH = "MANUFACTURER_MISMATCH"
    COUNTERFEIT = "COUNTERFEIT"
    NOT_IN_DATABASE = "NOT_IN_DATABASE"


class ScanStatus(str, Enum):
    """Scan extraction status."""
    EXTRACTED = "EXTRACTED"
    NEED_BOTTOM_SCAN = "NEED_BOTTOM_SCAN"


class ActionRequired(str, Enum):
    """Actions required from frontend."""
    NONE = "NONE"
    VERIFY = "VERIFY"
    SCAN_BOTTOM = "SCAN_BOTTOM"
    MANUAL_REVIEW = "MANUAL_REVIEW"


class VerificationCheck(BaseModel):
    """Individual verification check result with reason."""
    status: bool = Field(..., description="Whether this check passed")
    expected: Optional[Any] = Field(None, description="Expected value from database")
    actual: Optional[Any] = Field(None, description="Actual value detected/provided")
    reason: Optional[str] = Field(None, description="Detailed reason if check failed")


class ScanExtractResult(BaseModel):
    """Result of image extraction (Phase 1 of scan workflow)."""
    scan_id: UUID = Field(..., description="Unique identifier for this scan")
    status: ScanStatus = Field(..., description="EXTRACTED or NEED_BOTTOM_SCAN")
    action_required: ActionRequired = Field(..., description="Recommended next action")
    confidence_score: float = Field(..., ge=0, le=100, description="OCR confidence (0-100)")
    ocr_text: str = Field(..., description="Raw OCR-extracted text")
    part_number_detected: str = Field(..., description="Best guess part number")
    part_number_candidates: List[str] = Field(..., description="All candidates from OCR")
    manufacturer_detected: Optional[str] = Field(None, description="Detected manufacturer")
    detected_pins: int = Field(..., ge=0, description="Number of pins detected")
    message: str = Field(..., description="Human-readable status message")
    scanned_at: datetime = Field(..., description="When image was scanned")

    class Config:
        json_schema_extra = {
            "example": {
                "scan_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "EXTRACTED",
                "action_required": "VERIFY",
                "confidence_score": 94.5,
                "ocr_text": "LM555CN\nTI\n2024",
                "part_number_detected": "LM555CN",
                "part_number_candidates": ["LM555CN", "LM555", "LM555CNTI"],
                "manufacturer_detected": "Texas Instruments",
                "detected_pins": 8,
                "message": "Data extracted successfully. Ready for verification.",
                "scanned_at": "2025-12-01T10:30:00Z"
            }
        }


class ScanVerifyRequest(BaseModel):
    """Request to verify extracted scan against database."""
    scan_id: UUID = Field(..., description="Reference to the extraction scan")
    part_number: Optional[str] = Field(None, description="Override part number")
    detected_pins: Optional[int] = Field(None, ge=0, description="Override detected pins")

    class Config:
        json_schema_extra = {
            "example": {
                "scan_id": "550e8400-e29b-41d4-a716-446655440000",
                "part_number": "LM555",
                "detected_pins": 8
            }
        }


class ScanVerifyResult(BaseModel):
    """Result of verification against database (Phase 2)."""
    scan_id: UUID = Field(..., description="Reference to original scan")
    verification_status: VerificationStatus = Field(..., description="Verification result")
    status: str = Field(..., description="Unified scan status for frontend compatibility")
    action_required: ActionRequired = Field(..., description="Recommended action")
    part_number: str = Field(..., description="Part number that was verified")
    matched_ic: Optional[Dict[str, Any]] = Field(None, description="IC spec if found")
    verification_checks: Dict[str, VerificationCheck] = Field(
        ..., 
        description="Individual check results with reasons"
    )
    confidence_score: float = Field(..., ge=0, le=100, description="Confidence in result")
    queued_for_sync: bool = Field(default=False, description="True if queued")
    queued_candidates: Optional[List[str]] = Field(None, description="Candidates queued")
    message: str = Field(..., description="Human-readable message")
    completed_at: datetime = Field(..., description="When verification completed")

    class Config:
        json_schema_extra = {
            "example": {
                "scan_id": "550e8400-e29b-41d4-a716-446655440000",
                "verification_status": "MATCH_FOUND",
                "action_required": "NONE",
                "part_number": "LM555",
                "matched_ic": {
                    "part_number": "LM555",
                    "manufacturer": "TI",
                    "pin_count": 8,
                    "package_type": "DIP"
                },
                "verification_checks": {
                    "part_number_match": {
                        "status": True,
                        "expected": "LM555",
                        "actual": "LM555CN",
                        "reason": None
                    },
                    "pin_count_match": {
                        "status": True,
                        "expected": 8,
                        "actual": 8,
                        "reason": None
                    }
                },
                "confidence_score": 98.5,
                "queued_for_sync": False,
                "message": "IC verified successfully. All checks passed.",
                "completed_at": "2025-12-01T10:35:00Z"
            }
        }
