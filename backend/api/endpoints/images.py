"""
Image upload API endpoints.
Handles image upload and preprocessing operations.
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Form, status
from fastapi.responses import JSONResponse
from typing import Optional
from datetime import datetime
import logging

from backend.schemas.images import (
    ImageUploadResponse,
    ImageUploadRequest,
    PreprocessingMetadata,
    ErrorResponse
)
from backend.services.storage import save_image_file
from backend.services.preprocessing import ImagePreprocessingPipeline, PreprocessingException
from backend.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/images",
    tags=["images"],
    responses={
        400: {"model": ErrorResponse, "description": "Bad Request"},
        413: {"model": ErrorResponse, "description": "Payload Too Large"},
        415: {"model": ErrorResponse, "description": "Unsupported Media Type"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"}
    }
)

# Initialize preprocessing pipeline
preprocessing_pipeline = ImagePreprocessingPipeline()


@router.post(
    "/upload",
    response_model=ImageUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and preprocess an image",
    description="""
    Upload an image file for IC analysis. The image will be:
    1. Validated for format and size
    2. Stored securely
    3. Preprocessed through a configurable pipeline
    
    Supported formats: JPEG, PNG, BMP, TIFF
    Maximum file size: 10MB
    """,
    responses={
        201: {
            "description": "Image uploaded and preprocessed successfully",
            "model": ImageUploadResponse
        }
    }
)
async def upload_image(
    file: UploadFile = File(
        ...,
        description="Image file to upload (JPEG, PNG, BMP, or TIFF)"
    ),
    denoise: bool = Form(
        default=True,
        description="Apply noise reduction to the image"
    ),
    enhance_contrast: bool = Form(
        default=False,
        description="Apply contrast enhancement"
    ),
    normalize: bool = Form(
        default=True,
        description="Normalize image pixel values"
    ),
    edge_prep: bool = Form(
        default=False,
        description="Prepare image for edge detection"
    )
) -> ImageUploadResponse:
    """
    Upload and preprocess an image for IC verification.
    
    This endpoint handles the complete image ingestion workflow:
    - File validation (format, size, content type)
    - Secure storage
    - Preprocessing pipeline execution
    
    Args:
        file: The uploaded image file
        denoise: Whether to apply denoising
        enhance_contrast: Whether to enhance contrast
        normalize: Whether to normalize the image
        edge_prep: Whether to prepare for edge detection
        
    Returns:
        ImageUploadResponse with upload details and preprocessing results
        
    Raises:
        HTTPException: For various error conditions (invalid format, too large, etc.)
    """
    uploaded_at = datetime.utcnow()
    
    try:
        # Validate content type
        if not file.content_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=create_error_detail(
                    "Content type not specified",
                    "CONTENT_TYPE_MISSING"
                )
            )
        
        if file.content_type not in settings.ALLOWED_IMAGE_TYPES:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=create_error_detail(
                    f"Unsupported image type. Allowed types: {', '.join(settings.ALLOWED_IMAGE_TYPES)}",
                    "UNSUPPORTED_IMAGE_TYPE"
                )
            )
        
        # Validate filename
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=create_error_detail(
                    "Filename is required",
                    "FILENAME_MISSING"
                )
            )
        
        # Read file content
        content = await file.read()
        file_size = len(content)
        
        # Validate file size
        if file_size == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=create_error_detail(
                    "Empty file uploaded",
                    "EMPTY_FILE"
                )
            )
        
        if file_size > settings.MAX_IMAGE_SIZE_BYTES:
            max_size_mb = settings.MAX_IMAGE_SIZE_BYTES / (1024 * 1024)
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=create_error_detail(
                    f"File too large. Maximum size is {max_size_mb:.1f}MB",
                    "FILE_TOO_LARGE"
                )
            )
        
        logger.info(f"Processing upload: {file.filename} ({file_size} bytes, {file.content_type})")
        
        # Save the image file
        try:
            image_id, file_path = save_image_file(content, file.filename)
            logger.info(f"Image saved with ID: {image_id} at {file_path}")
        except Exception as e:
            logger.error(f"Failed to save image: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=create_error_detail(
                    "Failed to save uploaded file",
                    "STORAGE_ERROR"
                )
            )
        
        # Prepare preprocessing options
        preprocessing_options = {
            "denoise": denoise,
            "enhance_contrast": enhance_contrast,
            "normalize": normalize,
            "edge_prep": edge_prep
        }
        
        # Run preprocessing pipeline
        try:
            preprocessing_result = await preprocessing_pipeline.process(
                file_path,
                options=preprocessing_options
            )
            logger.info(f"Preprocessing completed for image {image_id}")
        except PreprocessingException as e:
            logger.error(f"Preprocessing failed for image {image_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=create_error_detail(
                    f"Preprocessing failed: {str(e)}",
                    "PREPROCESSING_ERROR"
                )
            )
        except Exception as e:
            logger.error(f"Unexpected preprocessing error for image {image_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=create_error_detail(
                    "Unexpected error during preprocessing",
                    "INTERNAL_ERROR"
                )
            )
        
        # Build preprocessing metadata
        preprocessing_metadata = PreprocessingMetadata(
            steps_applied=preprocessing_result.get("steps_applied", []),
            processed_at=preprocessing_result.get("processed_at", datetime.utcnow().isoformat()),
            options_used=preprocessing_options,
            validation=preprocessing_result.get("validation")
        )
        
        # Build response
        response = ImageUploadResponse(
            image_id=image_id,
            filename=file.filename,
            content_type=file.content_type,
            size_bytes=file_size,
            file_path=str(file_path),
            preprocessing=preprocessing_metadata,
            uploaded_at=uploaded_at.isoformat()
        )
        
        logger.info(f"Successfully processed image upload: {image_id}")
        return response
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        # Catch-all for unexpected errors
        logger.error(f"Unexpected error in upload_image: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=create_error_detail(
                "An unexpected error occurred",
                "INTERNAL_ERROR"
            )
        )


def create_error_detail(message: str, error_code: str) -> dict:
    """
    Create a standardized error detail dictionary.
    
    Args:
        message: Human-readable error message
        error_code: Machine-readable error code
        
    Returns:
        Dictionary with error details
    """
    return {
        "detail": message,
        "error_code": error_code,
        "timestamp": datetime.utcnow().isoformat()
    }
