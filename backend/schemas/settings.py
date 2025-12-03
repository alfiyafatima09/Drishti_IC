"""Pydantic schemas for settings operations."""
from pydantic import BaseModel
from typing import Any


class SettingsResponse(BaseModel):
    """All settings response."""
    settings: dict[str, Any]


class SettingsUpdateRequest(BaseModel):
    """Request to update settings."""
    # Accept any key-value pairs
    class Config:
        extra = "allow"


class SettingsUpdateResponse(BaseModel):
    """Response after updating settings."""
    success: bool
    message: str
    updated_settings: dict[str, Any]

