"""Datasheet Queue model - Pending ICs for online scraping."""
from sqlalchemy import Column, Integer, String, Text, DateTime, func

from backend.models.base import Base, TimestampMixin


class DatasheetQueue(Base, TimestampMixin):
    """
    Queue of unknown IC part numbers waiting for online scraping.
    Entries are processed during weekly sync when internet is available.
    """
    __tablename__ = "datasheet_queue"

    id = Column(Integer, primary_key=True, autoincrement=True)
    part_number = Column(String(100), unique=True, nullable=False, index=True)
    first_seen_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    last_scanned_at = Column(DateTime(timezone=True), server_default=func.now())
    scan_count = Column(Integer, default=1)  # Times scanned while unknown
    status = Column(String(20), default="PENDING", index=True)  # PENDING, PROCESSING, FAILED
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)

    def __repr__(self):
        return f"<DatasheetQueue(part_number='{self.part_number}', status='{self.status}')>"

    def to_dict(self):
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

