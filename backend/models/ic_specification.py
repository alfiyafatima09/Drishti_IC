"""IC Specification model - Golden Record database."""
from sqlalchemy import Column, Integer, String, Float, Text, Boolean, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import JSONB

from models.base import Base, TimestampMixin
from core.constants import (
    Manufacturer,
    ICSource,
    MANUFACTURER_NAMES,
    get_supported_manufacturers,
    is_valid_manufacturer,
)


class ICSpecification(Base, TimestampMixin):
    """
    Golden Record table containing verified IC specifications.
    This is the source of truth for IC verification.
    
    Note: Same part_number can have multiple entries from different manufacturers.
    Unique constraint is on (part_number, manufacturer) composite key.
    """
    __tablename__ = "ic_specifications"
    __table_args__ = (
        # Composite unique constraint: same IC can exist from different manufacturers
        UniqueConstraint('part_number', 'manufacturer', name='uq_ic_part_manufacturer'),
        # Composite index for efficient lookups
        Index('idx_ic_specs_part_mfr', 'part_number', 'manufacturer'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    part_number = Column(String(100), nullable=False, index=True)
    manufacturer = Column(String(100), nullable=False, index=True)  # Enum: STM, TI, etc.
    pin_count = Column(Integer, nullable=False)
    package_type = Column(String(50))  # DIP, QFN, BGA, SOIC, LQFP, etc.
    description = Column(Text)
    datasheet_url = Column(String(500))  # Original web URL where datasheet was downloaded
    datasheet_path = Column(String(500))  # Local file path (e.g., /datasheets/ti/lm555.pdf)
    has_datasheet = Column(Boolean, default=False)  # Whether PDF is available locally
    voltage_min = Column(Float)
    voltage_max = Column(Float)
    operating_temp_min = Column(Float)
    operating_temp_max = Column(Float)
    electrical_specs = Column(JSONB, default={})  # Flexible JSON field for additional specs
    source = Column(String(50), default=ICSource.MANUAL.value)  # MANUAL, SCRAPED_STM, SCRAPED_TI, etc.

    def __repr__(self):
        return f"<ICSpecification(part_number='{self.part_number}', manufacturer='{self.manufacturer}', pin_count={self.pin_count})>"

    @property
    def manufacturer_name(self) -> str:
        """Get full manufacturer name from code."""
        try:
            mfr = Manufacturer(self.manufacturer)
            return MANUFACTURER_NAMES.get(mfr, self.manufacturer)
        except ValueError:
            return self.manufacturer

    @staticmethod
    def get_supported_manufacturers() -> list[str]:
        """Get list of supported manufacturer codes."""
        return get_supported_manufacturers()

    @staticmethod
    def is_valid_manufacturer(code: str) -> bool:
        """Check if manufacturer code is valid."""
        return is_valid_manufacturer(code)

    def to_dict(self) -> dict:
        """Convert model to dictionary."""
        return {
            "part_number": self.part_number,
            "manufacturer": self.manufacturer,
            "manufacturer_name": self.manufacturer_name,
            "pin_count": self.pin_count,
            "package_type": self.package_type,
            "description": self.description,
            "datasheet_url": self.datasheet_url,
            "datasheet_path": self.datasheet_path,
            "has_datasheet": self.has_datasheet,
            "voltage_min": self.voltage_min,
            "voltage_max": self.voltage_max,
            "operating_temp_min": self.operating_temp_min,
            "operating_temp_max": self.operating_temp_max,
            "electrical_specs": self.electrical_specs or {},
            "source": self.source,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def to_search_result(self) -> dict:
        """Convert to abbreviated format for search results."""
        return {
            "part_number": self.part_number,
            "manufacturer": self.manufacturer,
            "manufacturer_name": self.manufacturer_name,
            "pin_count": self.pin_count,
            "package_type": self.package_type,
            "description": self.description,
            "has_datasheet": self.has_datasheet,
        }
