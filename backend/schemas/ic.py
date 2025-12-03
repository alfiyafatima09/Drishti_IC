"""Pydantic schemas for IC specifications."""
from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime


class ICSpecificationBase(BaseModel):
    """Base IC specification fields."""
    part_number: str
    manufacturer: Optional[str] = None
    pin_count: int
    package_type: Optional[str] = None
    description: Optional[str] = None


class ICSpecificationCreate(ICSpecificationBase):
    """Schema for creating a new IC specification."""
    datasheet_url: Optional[str] = None
    datasheet_path: Optional[str] = None
    voltage_min: Optional[float] = None
    voltage_max: Optional[float] = None
    operating_temp_min: Optional[float] = None
    operating_temp_max: Optional[float] = None
    electrical_specs: Optional[dict[str, Any]] = None
    source: str = "MANUAL"


class ICSpecificationResponse(ICSpecificationBase):
    """Schema for IC specification responses."""
    datasheet_url: Optional[str] = None
    datasheet_path: Optional[str] = None
    has_datasheet: bool = False
    voltage_min: Optional[float] = None
    voltage_max: Optional[float] = None
    operating_temp_min: Optional[float] = None
    operating_temp_max: Optional[float] = None
    electrical_specs: Optional[dict[str, Any]] = None
    source: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ICSearchResult(BaseModel):
    """Schema for IC search results."""
    results: list[ICSpecificationBase]
    total_count: int
    limit: int
    offset: int

