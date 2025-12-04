"""Common schema types used across the API."""
from pydantic import BaseModel
from typing import Optional, Any
from enum import Enum


class ScanStatus(str, Enum):
    """Possible scan result statuses."""
    PASS = "PASS"
    FAIL = "FAIL"
    PARTIAL = "PARTIAL"
    UNKNOWN = "UNKNOWN"
    COUNTERFEIT = "COUNTERFEIT"


class ActionRequired(str, Enum):
    """Actions that may be required after a scan."""
    NONE = "NONE"
    SCAN_BOTTOM = "SCAN_BOTTOM"


class QueueStatus(str, Enum):
    """Status of items in the datasheet queue."""
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    FAILED = "FAILED"


class FakeSource(str, Enum):
    """Source of fake registry entries."""
    SYNC_NOT_FOUND = "SYNC_NOT_FOUND"
    MANUAL_REPORT = "MANUAL_REPORT"


class SyncStatus(str, Enum):
    """Status of sync jobs."""
    IDLE = "IDLE"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    ERROR = "ERROR"
    CANCELLED = "CANCELLED"


class CaptureType(str, Enum):
    """Type of camera capture."""
    TOP = "TOP"
    BOTTOM = "BOTTOM"


class PartNumberSource(str, Enum):
    """Source/confidence level of part number identification."""
    DATABASE_MATCH = "database_match"      # Verified - found in database
    OCR_BEST_GUESS = "ocr_best_guess"      # Not found - using heuristic best guess
    MANUAL_OVERRIDE = "manual_override"    # Operator corrected it


class SuccessResponse(BaseModel):
    """Generic success response."""
    success: bool = True
    message: str


class ErrorResponse(BaseModel):
    """Generic error response."""
    error: str
    message: str
    suggestion: Optional[str] = None
    details: Optional[dict[str, Any]] = None

