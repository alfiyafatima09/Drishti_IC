"""Datasheet Queue model - Pending ICs for online scraping."""
from sqlalchemy import Column, Integer, String, Text, DateTime, func

from models.base import Base, TimestampMixin
from core.constants import QueueStatus


class DatasheetQueue(Base, TimestampMixin):
    """
    Queue of unknown IC part numbers waiting for online scraping.
    Entries are processed during weekly sync when internet is available.
    
    Lifecycle:
    1. Entry: When a scanned IC is not found in ic_specifications
    2. Processing: During sync job, status changes to PROCESSING
    3. Success: Record deleted, data inserted into ic_specifications
    4. Failure (recoverable): Status → FAILED, retry_count incremented
    5. Failure (permanent): After max retries, moved to fake_registry
    """
    __tablename__ = "datasheet_queue"

    # Valid status values from constants
    VALID_STATUSES = [s.value for s in QueueStatus]

    id = Column(Integer, primary_key=True, autoincrement=True)
    part_number = Column(String(100), unique=True, nullable=False, index=True)
    first_seen_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    last_scanned_at = Column(DateTime(timezone=True), server_default=func.now())
    scan_count = Column(Integer, default=1)  # Times scanned while unknown
    # Status: PENDING, PROCESSING, FAILED (from QueueStatus enum)
    status = Column(String(20), default=QueueStatus.PENDING.value, index=True)
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)

    def __repr__(self):
        return f"<DatasheetQueue(part_number='{self.part_number}', status='{self.status}')>"

    @classmethod
    def is_valid_status(cls, status: str) -> bool:
        """Check if status value is valid."""
        return status in cls.VALID_STATUSES

    def to_dict(self) -> dict:
        """Convert model to dictionary."""
        return {
            "part_number": self.part_number,
            "first_seen_at": self.first_seen_at.isoformat() if self.first_seen_at else None,
            "last_scanned_at": self.last_scanned_at.isoformat() if self.last_scanned_at else None,
            "scan_count": self.scan_count,
            "status": self.status,
            "retry_count": self.retry_count,
            "error_message": self.error_message,
        }
