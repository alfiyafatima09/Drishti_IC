"""Application Settings model - System configuration stored in database."""
from sqlalchemy import Column, Integer, String, Text, DateTime, func

from models.base import Base
from core.constants import SettingValueType


class AppSettings(Base):
    """
    System configuration stored in database.
    Settings can be updated at runtime without restarting the server.
    """
    __tablename__ = "settings"

    # Valid value types from constants
    VALID_VALUE_TYPES = [t.value for t in SettingValueType]

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(Text, nullable=False)
    # value_type: STRING, INTEGER, FLOAT, BOOLEAN, JSON (from SettingValueType enum)
    value_type = Column(String(20), default=SettingValueType.STRING.value)
    description = Column(Text)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    updated_by = Column(String(100))

    def __repr__(self):
        return f"<AppSettings(key='{self.key}', value='{self.value}')>"

    @classmethod
    def is_valid_value_type(cls, value_type: str) -> bool:
        """Check if value_type is valid."""
        return value_type in cls.VALID_VALUE_TYPES

    def get_typed_value(self):
        """Get value converted to appropriate type."""
        if self.value_type == SettingValueType.INTEGER.value:
            return int(self.value)
        elif self.value_type == SettingValueType.FLOAT.value:
            return float(self.value)
        elif self.value_type == SettingValueType.BOOLEAN.value:
            return self.value.lower() in ("true", "1", "yes")
        elif self.value_type == SettingValueType.JSON.value:
            import json
            return json.loads(self.value)
        return self.value

    def to_dict(self) -> dict:
        """Convert model to dictionary."""
        return {
            "key": self.key,
            "value": self.get_typed_value(),
            "value_type": self.value_type,
            "description": self.description,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "updated_by": self.updated_by,
        }
