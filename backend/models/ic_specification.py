"""IC Specification model - Golden Record database."""
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB

from backend.models.base import Base, TimestampMixin


class ICSpecification(Base, TimestampMixin):
    """
    Golden Record table containing verified IC specifications.
    This is the source of truth for IC verification.
    """
    __tablename__ = "ic_specifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    part_number = Column(String(100), unique=True, nullable=False, index=True)
    manufacturer = Column(String(100), index=True)
    pin_count = Column(Integer, nullable=False)
    package_type = Column(String(50))  # DIP, QFN, BGA, SOIC, etc.
    description = Column(Text)
    datasheet_url = Column(String(500))  # Original web URL
    datasheet_path = Column(String(500))  # Local file path
    voltage_min = Column(Float)
    voltage_max = Column(Float)
    operating_temp_min = Column(Float)
    operating_temp_max = Column(Float)
    electrical_specs = Column(JSONB, default={})  # Flexible JSON field
    source = Column(String(50), default="MANUAL")  # MANUAL, SCRAPED_MOUSER, etc.

    def __repr__(self):
        return f"<ICSpecification(part_number='{self.part_number}', pin_count={self.pin_count})>"

    def to_dict(self):
        """Convert model to dictionary."""
        return {
            "part_number": self.part_number,
            "manufacturer": self.manufacturer,
            "pin_count": self.pin_count,
            "package_type": self.package_type,
            "description": self.description,
            "datasheet_url": self.datasheet_url,
            "datasheet_path": self.datasheet_path,
            "has_datasheet": bool(self.datasheet_path),
            "voltage_min": self.voltage_min,
            "voltage_max": self.voltage_max,
            "operating_temp_min": self.operating_temp_min,
            "operating_temp_max": self.operating_temp_max,
            "electrical_specs": self.electrical_specs or {},
            "source": self.source,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

