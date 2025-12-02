"""Pydantic schemas for datasheet queue operations."""
from pydantic import BaseModel
from typing import Optional
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
    """List of queue items with counts."""
    queue_items: list[QueueItem]
    total_count: int
    pending_count: int
    failed_count: int

