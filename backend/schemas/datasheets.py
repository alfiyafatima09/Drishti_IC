"""
Datasheet download schemas.
Defines request and response models for datasheet operations.
"""
from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime


class DatasheetDownloadRequest(BaseModel):
    """Request model for downloading IC datasheet."""
    
    manufacturer: Literal["STM", "TI"] = Field(
        ...,
        description="Manufacturer name (STM = STMicroelectronics, TI = Texas Instruments)",
        example="STM"
    )
    
    ic_id: str = Field(
        ...,
        description="IC identifier (e.g., 'stm32l031k6' for STM, 'lm358' for TI)",
        example="stm32l031k6"
    )
    
    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "manufacturer": "STM",
                    "ic_id": "stm32l031k6"
                },
                {
                    "manufacturer": "TI",
                    "ic_id": "lm358"
                }
            ]
        }


class DatasheetDownloadResponse(BaseModel):
    """Response model for datasheet download operation."""
    
    success: bool = Field(..., description="Whether the download was successful")
    message: str = Field(..., description="Status message")
    manufacturer: str = Field(..., description="Manufacturer name")
    ic_id: str = Field(..., description="IC identifier")
    file_path: Optional[str] = Field(None, description="Local path where datasheet was saved")
    file_size_bytes: Optional[int] = Field(None, description="Size of downloaded file in bytes")
    downloaded_at: Optional[datetime] = Field(None, description="Timestamp of download")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Datasheet downloaded successfully",
                "manufacturer": "STM",
                "ic_id": "stm32l031k6",
                "file_path": "datasheets/stm/stm32l031k6.pdf",
                "file_size_bytes": 1024000,
                "downloaded_at": "2025-12-02T10:30:00Z"
            }
        }


class ErrorResponse(BaseModel):
    """Error response model."""
    
    error: str = Field(..., description="Error code")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[dict] = Field(None, description="Additional error details")
