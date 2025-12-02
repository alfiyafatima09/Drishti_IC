"""Fake Registry model - Known counterfeit/non-existent IC numbers."""
from sqlalchemy import Column, Integer, String, Text, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB

from backend.models.base import Base


class FakeRegistry(Base):
    """
    Registry of confirmed fake or non-existent IC part numbers.
    ICs in this table are immediately flagged as COUNTERFEIT when scanned.
    """
    __tablename__ = "fake_registry"

    id = Column(Integer, primary_key=True, autoincrement=True)
    part_number = Column(String(100), unique=True, nullable=False, index=True)
    source = Column(String(20), nullable=False)  # SYNC_NOT_FOUND, MANUAL_REPORT
    reason = Column(Text)
    reported_by = Column(String(100))  # Operator name for manual reports
    scrape_attempts = Column(Integer, default=0)
    manufacturers_checked = Column(JSONB)  # List of sites checked
    added_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<FakeRegistry(part_number='{self.part_number}', source='{self.source}')>"

    def to_dict(self):
        """Convert model to dictionary."""
        return {
            "part_number": self.part_number,
            "source": self.source,
            "reason": self.reason,
            "reported_by": self.reported_by,
            "scrape_attempts": self.scrape_attempts,
            "manufacturers_checked": self.manufacturers_checked,
            "added_at": self.added_at.isoformat() if self.added_at else None,
        }

    def to_info(self):
        """Convert to abbreviated format for scan responses."""
        return {
            "added_at": self.added_at.isoformat() if self.added_at else None,
            "source": self.source,
            "reason": self.reason,
        }

