"""Application Settings model - System configuration stored in database."""
from sqlalchemy import Column, Integer, String, Text, DateTime, func

from backend.models.base import Base


class AppSettings(Base):
    """
    System configuration stored in database.
    Settings can be updated at runtime without restarting the server.
    """
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(Text, nullable=False)
    value_type = Column(String(20), default="STRING")  # STRING, INTEGER, FLOAT, BOOLEAN, JSON
    description = Column(Text)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    updated_by = Column(String(100))

    def __repr__(self):
        return f"<AppSettings(key='{self.key}', value='{self.value}')>"

    def get_typed_value(self):
        """Get value converted to appropriate type."""
        if self.value_type == "INTEGER":
            return int(self.value)
        elif self.value_type == "FLOAT":
            return float(self.value)
        elif self.value_type == "BOOLEAN":
            return self.value.lower() in ("true", "1", "yes")
        elif self.value_type == "JSON":
            import json
            return json.loads(self.value)
        return self.value

    def to_dict(self):
        """Convert model to dictionary."""
        return {
            "key": self.key,
            "value": self.get_typed_value(),
            "value_type": self.value_type,
            "description": self.description,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "updated_by": self.updated_by,
        }

