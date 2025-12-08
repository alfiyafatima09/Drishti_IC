"""
IC Analysis API endpoint.
Upload IC images for OCR text extraction and pin count detection using Local Model.
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, status  # pyright: ignore[reportMissingImports]
from datetime import datetime
import logging
import uuid
import time
import asyncio
import tempfile
import os

from core.constants import MANUFACTURER_KEYWORDS
from schemas.ic_analysis import (
    ICAnalysisResult,
    OCRTextData,
    PinDetectionData,
    DimensionData,
    ErrorResponse
)
from services.storage import save_image_file
from services.ocr import extract_text_from_image
from services.llm import LLM
from services.dimension_service import DimensionService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/ic-analysis",
    tags=["IC Analysis"],
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
    
    **Powered by:** Local Vision Model (Qwen3-VL)
    
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
    Analyze IC chip image using Local Model and OCR.
    
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
        
        # ========== OCR Processing ==========
        logger.debug(f"[{analysis_id}] Starting OCR extraction...")
        ocr_response = extract_text_from_image(image_bytes, preprocess=True)
        
        if ocr_response.status == "error":
            logger.error(f"[{analysis_id}] OCR failed: {ocr_response.error}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error": "OCR_ERROR",
                    "message": f"OCR processing failed: {ocr_response.error}",
                    "details": {
                        "analysis_id": analysis_id
                    }
                }
            )
        
        # Calculate OCR confidence
        ocr_confidence = 0.0
        if ocr_response.results:
            ocr_confidence = sum(r.confidence for r in ocr_response.results) / len(ocr_response.results) * 100
        
        # Extract part number and manufacturer from OCR text
        ocr_text = ocr_response.full_text
        ocr_lines = [r.text.strip() for r in ocr_response.results if r.text.strip()]
        
        # Simple heuristic for part number (first substantial line)
        part_number = None
        if ocr_lines:
            # Try to find a line that looks like a part number
            for line in ocr_lines:
                if len(line) >= 3 and any(c.isdigit() for c in line) and any(c.isalpha() for c in line):
                    part_number = line
                    break
            if not part_number:
                part_number = ocr_lines[0] if ocr_lines else None
        
        # Extract manufacturer from OCR
        manufacturer = None
        for text_segment in ocr_response.texts:
            upper_text = text_segment.upper()
            for keyword in MANUFACTURER_KEYWORDS:
                if keyword in upper_text:
                    manufacturer = text_segment
                    break
            if manufacturer:
                break
        
        # Build OCR data
        ocr_data = OCRTextData(
            raw_text=ocr_text,
            part_number=part_number,
            manufacturer=manufacturer,
            date_code=None,  # Could be extracted with more sophisticated parsing
            lot_code=None,   # Could be extracted with more sophisticated parsing
            other_markings=ocr_lines[1:] if len(ocr_lines) > 1 else [],
            confidence_score=round(ocr_confidence, 2)
        )
        
        # ========== Vision Analysis (Local Model) for Pin Detection ==========
        pin_count = 0
        package_type = None
        pin_confidence = 0.0
        
        try:
            # Save image to temp file for LLM analysis
            with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp_file:
                tmp_file.write(image_bytes)
                tmp_path = tmp_file.name
            
            try:
                llm_client = LLM()
                llm_result = await asyncio.to_thread(llm_client.analyze_image, tmp_path)
                logger.info(f"[{analysis_id}] Vision analysis successful: {llm_result}")
                
                # Parse pin count
                pin_count_str = llm_result.get("pin_count", "")
                if pin_count_str:
                    try:
                        pin_count = int(pin_count_str)
                        pin_confidence = 90.0  # High confidence for vision-based detection
                    except (ValueError, TypeError):
                        logger.warning(f"[{analysis_id}] Could not parse pin count: {pin_count_str}")
                
                # Get manufacturer from vision if not found in OCR
                if not manufacturer and llm_result.get("manufacturer"):
                    manufacturer = llm_result.get("manufacturer")
                    ocr_data.manufacturer = manufacturer
                
                # Infer package type from pin count (simple heuristic)
                if pin_count > 0:
                    if pin_count <= 8:
                        package_type = "DIP-8" if pin_count == 8 else f"DIP-{pin_count}"
                    elif pin_count <= 16:
                        package_type = f"SOIC-{pin_count}"
                    elif pin_count <= 32:
                        package_type = f"QFP-{pin_count}"
                    else:
                        package_type = f"BGA/QFN-{pin_count}"
                
            finally:
                # Clean up temp file
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
                    
        except Exception as e:
            logger.error(f"[{analysis_id}] Vision analysis failed: {e}", exc_info=True)
            # Don't fail the entire request, just log and continue with OCR-only results
            pin_confidence = 0.0
        
        # Build pin detection data
        pin_data = PinDetectionData(
            pin_count=pin_count,
            package_type=package_type,
            pin_layout=f"{package_type or 'Unknown'} package, {pin_count} pins total" if pin_count > 0 else None,
            confidence_score=round(pin_confidence, 2),
            detection_method="Local Vision Model (Qwen3-VL)"
        )
        
        # ========== Dimension Measurement ==========
        dimension_data = None
        try:
            logger.debug(f"[{analysis_id}] Starting dimension measurement...")
            dim_result = await asyncio.to_thread(
                DimensionService.measure_from_bytes, 
                image_bytes
            )
            
            if dim_result:
                # Save visualization image
                vis_filename = f"measured_{image_id}.png"
                vis_path = os.path.join(os.path.dirname(image_path), vis_filename)
                
                await asyncio.to_thread(
                    DimensionService.save_visualization,
                    dim_result['visualization'],
                    vis_path
                )
                
                dimension_data = DimensionData(
                    width_mm=dim_result['width_mm'],
                    height_mm=dim_result['height_mm'],
                    width_px=dim_result['width_px'],
                    height_px=dim_result['height_px'],
                    area_mm2=dim_result['area_mm2'],
                    angle=dim_result['angle'],
                    confidence=dim_result['confidence'],
                    visualization_path=vis_path
                )
                logger.info(f"[{analysis_id}] Dimension measurement: {dim_result['width_mm']:.2f}mm x {dim_result['height_mm']:.2f}mm")
            else:
                logger.warning(f"[{analysis_id}] Dimension measurement failed - could not detect IC boundaries")
                
        except Exception as e:
            logger.error(f"[{analysis_id}] Dimension measurement error: {e}", exc_info=True)
            # Don't fail the entire request, just continue without dimensions
        
        logger.info(f"[{analysis_id}] Analysis complete - Part: {ocr_data.part_number}, Pins: {pin_data.pin_count}")
        
        # Calculate processing time
        processing_time_ms = (time.time() - start_time) * 1000
        
        # Build response
        result = ICAnalysisResult(
            analysis_id=analysis_id,
            image_path=str(image_path),
            ocr_data=ocr_data,
            pin_data=pin_data,
            dimension_data=dimension_data,
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
    description="Check if the API is running and Local Model service is configured"
)
async def health_check():
    """API health check endpoint."""
    
    # Check if local model is accessible
    local_model_configured = False
    local_model_endpoint = None
    try:
        llm_client = LLM()
        # Just check if we can initialize (doesn't make actual request)
        local_model_configured = llm_client.endpoint is not None
        local_model_endpoint = llm_client.endpoint if local_model_configured else None
    except Exception as e:
        logger.warning(f"Local model not configured: {e}")
        local_model_configured = False
    
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "local_model": {
                "configured": local_model_configured,
                "status": "ready" if local_model_configured else "not_configured",
                "endpoint": local_model_endpoint
            },
            "ocr": {
                "configured": True,
                "status": "ready"
            }
        }
    }
