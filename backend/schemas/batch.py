"""Schemas for batch processing operations."""
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime


class BatchScanRequest(BaseModel):
    """Request for batch scanning."""
    pass  # Using file uploads directly


class BatchScanResult(BaseModel):
    """Result of initiating batch scan."""
    job_id: str
    status: str
    total_images: int
    message: str


class BatchProgress(BaseModel):
    """Progress information for batch job."""
    job_id: str
    status: str  # 'processing', 'completed', 'failed'
    progress_percentage: float
    processed_images: int
    total_images: int
    results: Optional[List[Dict[str, Any]]] = None
    estimated_time_remaining: Optional[float] = None  # seconds


class BatchImageResult(BaseModel):
    """Result for individual image in batch."""
    image_path: str
    classification: Dict[str, Any]
    result: Dict[str, Any]
    processing_time: float