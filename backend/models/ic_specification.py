"""IC Specification model - Golden Record database."""
from sqlalchemy import Column, Integer, String, Float, Text, Boolean, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB

from models.base import Base, TimestampMixin


class ICSpecification(Base, TimestampMixin):
    """
    Golden Record table containing verified IC specifications.
    This is the source of truth for IC verification.
    
    Note: Same part_number can have multiple entries from different manufacturers.
    Unique constraint is on (part_number, manufacturer) composite key.
    """
    __tablename__ = "ic_specifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    part_number = Column(String(100), nullable=False, index=True)
    manufacturer = Column(String(100), nullable=False, index=True)  # Enum: STM, TI, etc.
    pin_count = Column(Integer, nullable=False)
    package_type = Column(String(50))  # DIP, QFN, BGA, SOIC, LQFP, etc.
    description = Column(Text)
    datasheet_url = Column(String(500))  # Original web URL
    datasheet_path = Column(String(500))  # Local file path
    has_datasheet = Column(Boolean, default=False)  # Whether PDF is available locally
    voltage_min = Column(Float)
    voltage_max = Column(Float)
    operating_temp_min = Column(Float)
    operating_temp_max = Column(Float)
    dimension_length = Column(Float)  # Length in mm
    dimension_width = Column(Float)   # Width in mm
    dimension_height = Column(Float)  # Height in mm
    electrical_specs = Column(JSONB, default={})  # Flexible JSON field
    source = Column(String(50), default="MANUAL")  # MANUAL, SCRAPED_STM, SCRAPED_TI, etc.
    
    # Composite unique constraint: same IC can exist from different manufacturers
    __table_args__ = (
        UniqueConstraint('part_number', 'manufacturer', name='uq_ic_part_manufacturer'),
    )

    def __repr__(self):
        return f"<ICSpecification(part_number='{self.part_number}', pin_count={self.pin_count})>"

    def to_dict(self):
        """Convert model to dictionary."""
        from core.constants import get_manufacturer_name
        return {
            "part_number": self.part_number,
            "manufacturer": self.manufacturer,
            "manufacturer_name": get_manufacturer_name(self.manufacturer),
            "pin_count": self.pin_count,
            "package_type": self.package_type,
            "description": self.description,
            "datasheet_url": self.datasheet_url,
            "datasheet_path": self.datasheet_path,
            "has_datasheet": self.has_datasheet if self.has_datasheet is not None else bool(self.datasheet_path),
            "voltage_min": self.voltage_min,
            "voltage_max": self.voltage_max,
            "operating_temp_min": self.operating_temp_min,
            "operating_temp_max": self.operating_temp_max,
            "dimension_length": self.dimension_length,
            "dimension_width": self.dimension_width,
            "dimension_height": self.dimension_height,
            "electrical_specs": self.electrical_specs or {},
            "source": self.source,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

