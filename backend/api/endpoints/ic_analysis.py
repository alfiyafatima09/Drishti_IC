"""
IC Analysis API endpoint.
Upload IC images for OCR text extraction and pin count detection using Gemini AI.
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, status
from datetime import datetime
import logging
import uuid
import time

from schemas.ic_analysis import (
    ICAnalysisResult,
    ErrorResponse
)
from services.storage import save_image_file
from services.gemini_service import gemini_service, GeminiServiceException

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1",
    tags=["Core Inspection"],
    responses={
        400: {"model": ErrorResponse, "description": "Bad Request"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
        503: {"model": ErrorResponse, "description": "Service Unavailable"}
    }
)


@router.post(
    "/scan",
    response_model=ICAnalysisResult,
    status_code=status.HTTP_200_OK,
    summary="Upload Image for IC Inspection",
    description="""
    Primary endpoint for IC verification. Upload an IC image for analysis.
    
    **What it does:**
    1. **OCR Text Extraction**: Reads all visible text on the IC chip
       - Part number (e.g., LM555, STM32F407)
       - Manufacturer name
       - Date codes and lot codes
       - Other markings
    
    2. **Pin Count Detection**: Counts the number of pins/leads
       - Detects package type (DIP, SOIC, QFN, BGA, etc.)
       - Identifies pin layout
       - Provides confidence scores
    
    **Powered by:** Google Gemini 1.5 Flash AI
    
    **Supported formats:** JPEG, PNG, BMP, TIFF  
    **Max file size:** 10MB
    
    **Returns:** Complete analysis with OCR data and pin detection results
    
    **Example use case:** Scan an LM555 timer IC to verify part number and confirm 8-pin DIP package
    """
)
async def scan_ic_image(
    file: UploadFile = File(..., description="IC chip image (JPEG, PNG, BMP, TIFF)")
):
    """
    Analyze IC chip image using Gemini AI.
    
    Args:
        file: Uploaded image file
        
    Returns:
        ICAnalysisResult with OCR and pin detection data
        
    Raises:
        HTTPException: If image processing or AI analysis fails
    """
    analysis_id = str(uuid.uuid4())
    start_time = time.time()
    
    logger.info(f"[{analysis_id}] Received IC scan request: {file.filename}")
    
    # Validate file type
    if file.content_type not in ["image/jpeg", "image/jpg", "image/png", "image/bmp", "image/tiff"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "INVALID_FILE_TYPE",
                "message": f"Unsupported file type: {file.content_type}",
                "details": {
                    "received": file.content_type,
                    "allowed": ["image/jpeg", "image/png", "image/bmp", "image/tiff"]
                }
            }
        )
    
    try:
        # Read and save the image
        image_bytes = await file.read()
        
        # Validate file size
        if len(image_bytes) > 10 * 1024 * 1024:  # 10MB
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "FILE_TOO_LARGE",
                    "message": "Image file exceeds maximum size of 10MB",
                    "details": {"size_bytes": len(image_bytes), "max_bytes": 10485760}
                }
            )
        
        # Save image to storage
        image_id, image_path = save_image_file(image_bytes, file.filename or "ic_image.jpg")
        logger.info(f"[{analysis_id}] Image saved: {image_path}")
        
        # Analyze with Gemini AI
        try:
            ocr_data, pin_data = await gemini_service.analyze_ic(image_path)
            logger.info(f"[{analysis_id}] Analysis complete - Part: {ocr_data.part_number}, Pins: {pin_data.pin_count}")
            
        except GeminiServiceException as e:
            logger.error(f"[{analysis_id}] Gemini service error: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "error": "AI_SERVICE_ERROR",
                    "message": "AI analysis service is unavailable or failed",
                    "details": {
                        "service": "Google Gemini",
                        "error": str(e),
                        "suggestion": "Please check GEMINI_API_KEY configuration"
                    }
                }
            )
        
        # Calculate processing time
        processing_time_ms = (time.time() - start_time) * 1000
        
        # Build response
        result = ICAnalysisResult(
            analysis_id=analysis_id,
            image_path=str(image_path),
            ocr_data=ocr_data,
            pin_data=pin_data,
            analyzed_at=datetime.utcnow(),
            processing_time_ms=round(processing_time_ms, 2)
        )
        
        logger.info(f"[{analysis_id}] Analysis completed in {processing_time_ms:.2f}ms")
        return result
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
        
    except Exception as e:
        logger.exception(f"[{analysis_id}] Unexpected error during IC analysis")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "INTERNAL_ERROR",
                "message": "An unexpected error occurred during image analysis",
                "details": {
                    "analysis_id": analysis_id,
                    "error": str(e)
                }
            }
        )


@router.get(
    "/health",
    tags=["System"],
    summary="Health Check",
    description="Check if the API is running and Gemini service is configured"
)
async def health_check():
    """API health check endpoint."""
    
    gemini_configured = bool(gemini_service)
    
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "gemini_ai": {
                "configured": gemini_configured,
                "status": "ready" if gemini_configured else "not_configured"
            }
        }
    }
