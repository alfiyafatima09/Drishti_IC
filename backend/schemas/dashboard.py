"""Pydantic schemas for dashboard operations."""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from backend.schemas.common import SyncStatus


class RecentCounterfeit(BaseModel):
    """Recent counterfeit detection."""
    part_number: str
    scanned_at: datetime


class DashboardStats(BaseModel):
    """Dashboard statistics response."""
    total_scans: int = 0
    scans_today: int = 0
    scans_this_week: int = 0
    pass_count: int = 0
    fail_count: int = 0
    unknown_count: int = 0
    counterfeit_count: int = 0
    pass_rate_percentage: float = 0.0
    queue_size: int = 0
    fake_registry_size: int = 0
    database_ic_count: int = 0
    last_sync_at: Optional[datetime] = None
    last_sync_status: Optional[SyncStatus] = None
    recent_counterfeits: list[RecentCounterfeit] = []

