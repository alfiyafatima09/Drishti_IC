"""Pydantic schemas for fake registry operations."""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from backend.schemas.common import FakeSource


class FakeRegistryItem(BaseModel):
    """Single item in the fake registry."""
    part_number: str
    source: FakeSource
    reason: Optional[str] = None
    reported_by: Optional[str] = None
    added_at: datetime
    scrape_attempts: int = 0
    manufacturers_checked: Optional[list[str]] = None

    class Config:
        from_attributes = True


class FakeListResult(BaseModel):
    """List of fake registry items."""
    fake_ics: list[FakeRegistryItem]
    total_count: int


class MarkFakeRequest(BaseModel):
    """Request to mark an IC as fake."""
    part_number: str
    reason: str
    reported_by: Optional[str] = None

