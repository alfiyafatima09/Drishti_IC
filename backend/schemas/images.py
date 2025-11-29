from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class ImageUploadRequest(BaseModel):
    """Request model for image upload configuration."""
    
    denoise: bool = Field(default=True, description="Apply noise reduction")
    enhance_contrast: bool = Field(default=False, description="Apply contrast enhancement")
    normalize: bool = Field(default=True, description="Apply image normalization")
    edge_prep: bool = Field(default=False, description="Prepare for edge detection")
    
    class Config:
        json_schema_extra = {
            "example": {
                "denoise": True,
                "enhance_contrast": False,
                "normalize": True,
                "edge_prep": False
            }
        }


class PreprocessingMetadata(BaseModel):
    """Metadata about preprocessing operations."""
    
    steps_applied: List[str] = Field(..., description="List of preprocessing steps applied")
    processed_at: str = Field(..., description="ISO timestamp of when processing occurred")
    options_used: Dict[str, Any] = Field(..., description="Preprocessing options that were used")
    validation: Optional[Dict[str, Any]] = Field(None, description="Image validation results")


class ImageUploadResponse(BaseModel):
    """Response model for successful image upload."""
    
    image_id: str = Field(..., description="Unique identifier for the uploaded image")
    filename: str = Field(..., description="Original filename of the uploaded image")
    content_type: str = Field(..., description="MIME type of the uploaded image")
    size_bytes: int = Field(..., description="Size of the uploaded file in bytes")
    file_path: str = Field(..., description="Path where the image is stored")
    preprocessing: PreprocessingMetadata = Field(..., description="Preprocessing pipeline results")
    uploaded_at: str = Field(..., description="ISO timestamp of upload")
    
    class Config:
        json_schema_extra = {
            "example": {
                "image_id": "550e8400-e29b-41d4-a716-446655440000",
                "filename": "ic_chip_photo.jpg",
                "content_type": "image/jpeg",
                "size_bytes": 2048576,
                "file_path": "media/550e8400-e29b-41d4-a716-446655440000.jpg",
                "preprocessing": {
                    "steps_applied": ["denoise", "normalize"],
                    "processed_at": "2025-11-30T12:34:56.789Z",
                    "options_used": {"denoise": True, "normalize": True},
                    "validation": {"valid": True, "format": "JPEG"}
                },
                "uploaded_at": "2025-11-30T12:34:56.789Z"
            }
        }


class ErrorResponse(BaseModel):
    """Standard error response model."""
    
    detail: str = Field(..., description="Error message describing what went wrong")
    error_code: Optional[str] = Field(None, description="Machine-readable error code")
    timestamp: str = Field(..., description="ISO timestamp when error occurred")
    
    class Config:
        json_schema_extra = {
            "example": {
                "detail": "File too large. Maximum size is 10MB",
                "error_code": "FILE_TOO_LARGE",
                "timestamp": "2025-11-30T12:34:56.789Z"
            }
        }  