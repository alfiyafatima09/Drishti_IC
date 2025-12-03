"""
Datasheet management schemas.
Request and response models matching the API contract.
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Literal, get_args
from datetime import datetime

from core.constants import get_supported_manufacturers, Manufacturer

_supported_manufacturers = get_supported_manufacturers()
ManufacturerCode = Literal[*_supported_manufacturers] 


class DatasheetDownloadRequest(BaseModel):
    """Request model for downloading IC datasheet."""
    
    part_number: str = Field(
        ...,
        min_length=2,
        description="IC part number to download datasheet for",
        example="LM555"
    )
    
    manufacturer: Optional[ManufacturerCode] = Field(
        None,
        description=(
            f"Optional manufacturer code. "
            f"Supported: {', '.join(get_supported_manufacturers())}. "
            f"If provided, downloads only from this manufacturer. "
            f"If omitted, tries ALL supported manufacturers in parallel."
        ),
        example="TI"
    )
    
    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "part_number": "LM555",
                    "manufacturer": "TI"
                },
                {
                    "part_number": "LM555"
                }
            ]
        }


class DatasheetDownloadResult(BaseModel):
    """Result for a single manufacturer download attempt."""
    
    manufacturer: ManufacturerCode = Field(
        ...,
        description=f"Manufacturer code (one of: {', '.join(get_supported_manufacturers())})"
    )
    
    manufacturer_name: str = Field(
        ...,
        description="Full manufacturer name",
        example="Texas Instruments"
    )
    
    status: Literal["SUCCESS", "NOT_FOUND", "TIMEOUT", "ERROR"] = Field(
        ...,
        description="Download status"
    )
    
    file_path: Optional[str] = Field(
        None,
        description="Local path where PDF was saved (if successful)",
        example="/datasheets/ti/lm555.pdf"
    )
    
    file_size_bytes: Optional[int] = Field(
        None,
        description="File size in bytes (if successful)"
    )
    
    datasheet_url: Optional[str] = Field(
        None,
        description="URL where datasheet was downloaded from"
    )
    
    data_extracted: bool = Field(
        False,
        description="Whether IC data was successfully extracted from PDF"
    )
    
    error: Optional[str] = Field(
        None,
        description="Error message (if status is not SUCCESS)"
    )


class DatasheetDownloadResponse(BaseModel):
    """Response from datasheet download operation."""
    
    success: bool = Field(
        ...,
        description="True if at least one manufacturer succeeded"
    )
    
    part_number: str = Field(
        ...,
        description="The requested part number"
    )
    
    manufacturers_found: List[ManufacturerCode] = Field(
        ...,
        description="List of manufacturers where datasheet was found"
    )
    
    manufacturers_tried: List[ManufacturerCode] = Field(
        ...,
        description="List of all manufacturers attempted"
    )
    
    manufacturers_failed: List[ManufacturerCode] = Field(
        ...,
        description="List of manufacturers that failed"
    )
    
    results: List[DatasheetDownloadResult] = Field(
        ...,
        description="Detailed results for each manufacturer attempted"
    )
    
    database_entries_created: int = Field(
        ...,
        description="Number of new entries added to ic_specifications table"
    )
    
    message: str = Field(
        ...,
        description="Human-readable summary message"
    )


class ManufacturerDetail(BaseModel):
    """Detailed information about a manufacturer."""
    
    name: str = Field(..., description="Full manufacturer name")
    url_pattern: str = Field(..., description="URL pattern for datasheet downloads")
    example_ics: List[str] = Field(..., description="Example IC part numbers")


class ManufacturerListResponse(BaseModel):
    """Response for listing supported manufacturers."""
    
    manufacturers: List[ManufacturerCode] = Field(
        ...,
        description="List of supported manufacturer codes"
    )
    
    count: int = Field(
        ...,
        description="Total number of supported manufacturers"
    )
    
    details: dict[str, ManufacturerDetail] = Field(
        ...,
        description="Detailed information for each manufacturer"
    )


class ErrorResponse(BaseModel):
    """Error response model."""
    
    error: str = Field(..., description="Error code")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[dict] = Field(None, description="Additional error details")
