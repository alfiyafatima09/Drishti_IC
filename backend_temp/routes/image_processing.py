"""
Image processing routes for IC analysis
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import Optional
import os
from datetime import datetime

from models.database import get_db
from services.image_processing import ImageProcessingService
from config.settings import settings

router = APIRouter()
image_service = ImageProcessingService()


@router.post("/images/upload")
async def upload_image(
    file: UploadFile = File(...),
    preprocess: Optional[bool] = True,
    enhance_contrast: Optional[bool] = False
):
    """Upload and preprocess an image for IC analysis"""

    if file.filename.split('.')[-1].lower() not in settings.supported_image_formats:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format. Supported: {settings.supported_image_formats}"
        )

    try:
        
        content = await file.read()

        if len(content) > settings.max_image_size:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size: {settings.max_image_size} bytes"
            )

        result = await image_service.process_image(
            content,
            filename=file.filename,
            preprocess=preprocess,
            enhance_contrast=enhance_contrast
        )

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image processing failed: {str(e)}")


@router.post("/images/{image_id}/analyze")
async def analyze_image(
    image_id: str,
    analysis_type: Optional[str] = "full", 
    db: Session = Depends(get_db)
):
    """Analyze a previously uploaded image"""

    try:
        result = await image_service.analyze_image(image_id, analysis_type)
        return result

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Image not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image analysis failed: {str(e)}")


@router.get("/images/{image_id}")
async def get_image(image_id: str):
    """Get processed image by ID"""

    image_path = image_service.get_image_path(image_id)
    if not os.path.exists(image_path):
        raise HTTPException(status_code=404, detail="Image not found")

    return FileResponse(image_path, media_type="image/jpeg")


@router.get("/images/{image_id}/regions/{region_type}")
async def get_image_regions(image_id: str, region_type: str):
    """Get specific regions from processed image (text, logo, marking areas)"""

    try:
        regions = await image_service.extract_regions(image_id, region_type)
        return {"regions": regions}

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Image not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Region extraction failed: {str(e)}")


@router.post("/images/compare")
async def compare_images(
    reference_file: UploadFile = File(...),
    test_file: UploadFile = File(...),
    comparison_type: Optional[str] = "similarity"  
):
    """Compare two images for verification purposes"""

    try:
        ref_content = await reference_file.read()
        test_content = await test_file.read()

        result = await image_service.compare_images(
            ref_content, test_content, comparison_type
        )

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image comparison failed: {str(e)}")


@router.delete("/images/{image_id}")
async def delete_image(image_id: str):
    """Delete a processed image and its analysis results"""

    try:
        await image_service.delete_image(image_id)
        return {"message": "Image deleted successfully"}

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Image not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image deletion failed: {str(e)}")


@router.get("/images/{image_id}/metadata")
async def get_image_metadata(image_id: str):
    """Get metadata and analysis results for an image"""

    try:
        metadata = await image_service.get_image_metadata(image_id)
        return metadata

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Image not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Metadata retrieval failed: {str(e)}")
