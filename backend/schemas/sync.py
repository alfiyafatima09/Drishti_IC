"""Pydantic schemas for sync operations."""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID

from schemas.common import SyncStatus, QueueStatus


class SyncStartRequest(BaseModel):
    """Request to start a sync job."""
    max_items: Optional[int] = Field(None, description="Maximum number of items to process")
    retry_failed: bool = Field(True, description="Whether to retry previously failed items")
    status_filter: Optional[List[str]] = Field(
        None, 
        description="Only sync items with these statuses. Options: PENDING, FAILED"
    )


class SyncJobInfo(BaseModel):
    """Response when starting a sync job."""
    job_id: UUID
    status: SyncStatus = SyncStatus.PROCESSING
    message: str
    queue_size: int
    estimated_time_minutes: Optional[int] = None


class SyncStatusResponse(BaseModel):
    """Current sync job status."""
    job_id: Optional[UUID] = None
    status: SyncStatus
    progress_percentage: int = 0
    current_item: Optional[str] = None
    total_items: int = 0
    processed_items: int = 0
    success_count: int = 0
    failed_count: int = 0
    fake_count: int = 0
    started_at: Optional[datetime] = None
    estimated_completion: Optional[datetime] = None
    message: Optional[str] = None

    class Config:
        from_attributes = True


class SyncHistoryItem(BaseModel):
    """Single sync job in history."""
    job_id: UUID
    status: SyncStatus
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    total_items: int = 0
    success_count: int = 0
    failed_count: int = 0
    fake_count: int = 0

    class Config:
        from_attributes = True


class SyncHistoryResult(BaseModel):
    """List of past sync jobs."""
    sync_jobs: list[SyncHistoryItem]
    total_count: int
