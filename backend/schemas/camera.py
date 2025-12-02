"""Pydantic schemas for camera operations."""
from pydantic import BaseModel
from typing import Optional
from uuid import UUID

from backend.schemas.common import CaptureType


class CaptureRequest(BaseModel):
    """Request to capture a frame."""
    capture_type: CaptureType
    scan_id: Optional[UUID] = None  # Required for BOTTOM capture


class CaptureResponse(BaseModel):
    """Response after capturing a frame."""
    success: bool
    message: str
    scan_id: UUID

