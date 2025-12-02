"""Sync Job model - Tracking weekly sync operations."""
from sqlalchemy import Column, Integer, String, Text, DateTime, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid

from backend.models.base import Base


class SyncJob(Base):
    """
    Tracking table for weekly synchronization jobs.
    Records progress and results of each sync operation.
    """
    __tablename__ = "sync_jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4, index=True)
    status = Column(String(20), nullable=False, default="IDLE", index=True)  # IDLE, PROCESSING, COMPLETED, ERROR, CANCELLED
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    total_items = Column(Integer, default=0)
    processed_items = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)
    fake_count = Column(Integer, default=0)  # Items moved to fake registry
    current_item = Column(String(100))  # Currently processing IC
    error_message = Column(Text)
    log = Column(JSONB, default=[])  # Detailed per-item log
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<SyncJob(job_id='{self.job_id}', status='{self.status}')>"

    def to_dict(self):
        """Convert model to dictionary for status response."""
        return {
            "job_id": str(self.job_id) if self.job_id else None,
            "status": self.status,
            "progress_percentage": self._calculate_progress(),
            "current_item": self.current_item,
            "total_items": self.total_items,
            "processed_items": self.processed_items,
            "success_count": self.success_count,
            "failed_count": self.failed_count,
            "fake_count": self.fake_count,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "estimated_completion": None,  # TODO: Calculate based on progress
            "message": self.error_message,
        }

    def to_history_item(self):
        """Convert to abbreviated format for history list."""
        return {
            "job_id": str(self.job_id) if self.job_id else None,
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "total_items": self.total_items,
            "success_count": self.success_count,
            "failed_count": self.failed_count,
            "fake_count": self.fake_count,
        }

    def _calculate_progress(self) -> int:
        """Calculate progress percentage."""
        if self.total_items and self.total_items > 0:
            return int((self.processed_items / self.total_items) * 100)
        return 0

