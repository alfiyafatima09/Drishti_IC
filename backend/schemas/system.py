"""Pydantic schemas for system status."""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID

from schemas.common import SyncStatus


class HealthResponse(BaseModel):
    """Basic health check response."""
    status: str = "healthy"
    timestamp: datetime


class DatabaseStatus(BaseModel):
    """Database connection status."""
    connected: bool
    ic_count: int = 0


class CameraStatus(BaseModel):
    """Camera connection status."""
    connected: bool
    last_frame_at: Optional[datetime] = None


class NetworkStatus(BaseModel):
    """Network availability status."""
    internet_available: bool
    last_checked: Optional[datetime] = None


class QueueStatus(BaseModel):
    """Queue status summary."""
    pending_count: int = 0
    failed_count: int = 0


class StorageStatus(BaseModel):
    """Storage status."""
    datasheet_folder: str
    datasheet_count: int = 0
    folder_size_mb: float = 0.0


class LastSyncInfo(BaseModel):
    """Last sync job info."""
    job_id: Optional[UUID] = None
    status: Optional[SyncStatus] = None
    completed_at: Optional[datetime] = None


class SystemStatusResponse(BaseModel):
    """Comprehensive system status."""
    status: str  # operational, degraded, offline
    database: DatabaseStatus
    camera: CameraStatus
    network: NetworkStatus
    queue: QueueStatus
    storage: StorageStatus
    last_sync: Optional[LastSyncInfo] = None

