"""
IC Analysis schemas.
Request and response models for IC image analysis using Gemini AI.
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class OCRTextData(BaseModel):
    """Extracted text data from IC chip."""
    
    raw_text: str = Field(..., description="Raw text extracted from the IC")
    part_number: Optional[str] = Field(None, description="Detected IC part number")
    manufacturer: Optional[str] = Field(None, description="Detected manufacturer name")
    date_code: Optional[str] = Field(None, description="Manufacturing date code")
    lot_code: Optional[str] = Field(None, description="Lot/batch code")
    other_markings: List[str] = Field(default_factory=list, description="Other visible markings")
    confidence_score: float = Field(..., description="OCR confidence (0-100)", ge=0, le=100)


class PinDetectionData(BaseModel):
    """Pin count detection results."""
    
    pin_count: int = Field(..., description="Detected number of pins", ge=0)
    package_type: Optional[str] = Field(None, description="Detected package type (DIP, QFN, SOIC, etc.)")
    pin_layout: Optional[str] = Field(None, description="Pin layout description")
    confidence_score: float = Field(..., description="Detection confidence (0-100)", ge=0, le=100)
    detection_method: str = Field(..., description="Method used for detection")


class DimensionData(BaseModel):
    """IC chip dimension measurement results."""
    
    width_mm: float = Field(..., description="IC width in millimeters (including pins)")
    height_mm: float = Field(..., description="IC height in millimeters (including pins)")
    width_px: float = Field(..., description="IC width in pixels")
    height_px: float = Field(..., description="IC height in pixels")
    area_mm2: float = Field(..., description="IC area in square millimeters")
    angle: float = Field(..., description="Rotation angle of IC in degrees")
    confidence: str = Field(..., description="Detection confidence level (high/medium/low)")
    visualization_path: Optional[str] = Field(None, description="Path to annotated measurement image")


class ICAnalysisResult(BaseModel):
    """Complete IC analysis result."""
    
    analysis_id: str = Field(..., description="Unique analysis ID")
    image_path: str = Field(..., description="Path to analyzed image")
    ocr_data: OCRTextData = Field(..., description="OCR text extraction results")
    pin_data: PinDetectionData = Field(..., description="Pin detection results")
    dimension_data: Optional[DimensionData] = Field(None, description="IC dimension measurement results")
    analyzed_at: datetime = Field(..., description="Timestamp of analysis")
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")
    
    class Config:
        json_schema_extra = {
            "example": {
                "analysis_id": "550e8400-e29b-41d4-a716-446655440000",
                "image_path": "media/550e8400.jpg",
                "ocr_data": {
                    "raw_text": "LM555CN\nTEXAS INSTRUMENTS\n2023 43",
                    "part_number": "LM555",
                    "manufacturer": "Texas Instruments",
                    "date_code": "2023 43",
                    "lot_code": None,
                    "other_markings": ["CN"],
                    "confidence_score": 92.5
                },
                "pin_data": {
                    "pin_count": 8,
                    "package_type": "DIP-8",
                    "pin_layout": "Dual in-line, 8 pins total",
                    "confidence_score": 95.0,
                    "detection_method": "Gemini Vision Analysis"
                },
                "dimension_data": {
                    "width_mm": 9.53,
                    "height_mm": 6.35,
                    "width_px": 476.5,
                    "height_px": 317.5,
                    "area_mm2": 60.52,
                    "angle": -2.5,
                    "confidence": "high",
                    "visualization_path": "scanned_images/measured_550e8400.png"
                },
                "analyzed_at": "2025-12-02T10:30:00Z",
                "processing_time_ms": 1250.5
            }
        }


class ICAnalysisRequest(BaseModel):
    """Request model for IC analysis (multipart/form-data)."""
    
    # This will be handled by FastAPI's UploadFile in the endpoint
    # No fields needed here as it's just the image file
    pass


class ErrorResponse(BaseModel):
    """Error response model."""
    
    error: str = Field(..., description="Error code")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[dict] = Field(None, description="Additional error details")
