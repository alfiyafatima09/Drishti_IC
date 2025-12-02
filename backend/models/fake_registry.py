"""Fake Registry model - Known counterfeit/non-existent IC numbers."""
from sqlalchemy import Column, Integer, String, Text, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB

from models.base import Base
from core.constants import FakeSource


class FakeRegistry(Base):
    """
    Registry of confirmed fake or non-existent IC part numbers.
    ICs in this table are immediately flagged as COUNTERFEIT when scanned.
    
    Entry sources:
    - SYNC_NOT_FOUND: Automatically added after max sync retries failed
    - MANUAL_REPORT: Manually marked by an operator
    """
    __tablename__ = "fake_registry"

    # Valid source values from constants
    VALID_SOURCES = [s.value for s in FakeSource]

    id = Column(Integer, primary_key=True, autoincrement=True)
    part_number = Column(String(100), unique=True, nullable=False, index=True)
    # Source: SYNC_NOT_FOUND, MANUAL_REPORT (from FakeSource enum)
    source = Column(String(20), nullable=False)
    reason = Column(Text)
    reported_by = Column(String(100))  # Operator name for manual reports
    scrape_attempts = Column(Integer, default=0)
    manufacturers_checked = Column(JSONB)  # List of manufacturer codes checked
    added_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<FakeRegistry(part_number='{self.part_number}', source='{self.source}')>"

    @classmethod
    def is_valid_source(cls, source: str) -> bool:
        """Check if source value is valid."""
        return source in cls.VALID_SOURCES

    def to_dict(self) -> dict:
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

    def to_info(self) -> dict:
        """Convert to abbreviated format for scan responses."""
        return {
            "added_at": self.added_at.isoformat() if self.added_at else None,
            "source": self.source,
            "reason": self.reason,
        }
