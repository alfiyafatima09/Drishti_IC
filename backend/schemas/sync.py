"""Pydantic schemas for sync operations."""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID

from schemas.common import SyncStatus


class SyncStartRequest(BaseModel):
    """Request to start a sync job."""
    max_items: Optional[int] = None
    retry_failed: bool = True


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

