"""Pydantic schemas for datasheet queue operations."""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

from schemas.common import QueueStatus


class QueueItem(BaseModel):
    """Single item in the datasheet queue."""
    part_number: str
    first_seen_at: datetime
    last_scanned_at: Optional[datetime] = None
    scan_count: int = 1
    status: QueueStatus = QueueStatus.PENDING
    retry_count: int = 0
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


class QueueListResult(BaseModel):
    """List of queue items with counts and pagination."""
    queue_items: list[QueueItem]
    total_count: int
    pending_count: int
    failed_count: int
    limit: int = 100
    offset: int = 0


class QueueAddRequest(BaseModel):
    """Request to manually add part number(s) to the queue."""
    part_numbers: list[str] = Field(..., min_length=1, description="List of part numbers to add to queue")
    source: Optional[str] = Field(None, description="Optional source/reason for adding")


class QueueAddResponse(BaseModel):
    """Response after adding to queue."""
    success: bool = True
    added_count: int
    already_queued_count: int
    message: str
    queued_items: list[str]  # Part numbers that were added/updated
