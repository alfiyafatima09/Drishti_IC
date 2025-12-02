"""
Datasheet download API endpoints.
Multi-provider support for downloading datasheets from various manufacturers.
Supports: STM, Texas Instruments (TI), and extensible for more.
"""
from fastapi import APIRouter, HTTPException, status, Query
from fastapi.responses import JSONResponse
from datetime import datetime
import logging

from backend.schemas.datasheets import (
    DatasheetDownloadRequest,
    DatasheetDownloadResponse,
    ErrorResponse
)
from backend.services.datasheet import (
    datasheet_service,
    DatasheetDownloadException,
    UnsupportedManufacturerException
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/datasheets",
    tags=["datasheets"],
    responses={
        400: {"model": ErrorResponse, "description": "Bad Request"},
        404: {"model": ErrorResponse, "description": "Datasheet Not Found"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"}
    }
)


@router.post(
    "/download",
    response_model=DatasheetDownloadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Download IC Datasheet",
    description="""
    Download an IC datasheet from various manufacturers and store it locally.
    
    **Supported Manufacturers:**
    - **STM** (STMicroelectronics): stm32l031k6, stm32f407vg, etc.
    - **TI** (Texas Instruments): lm358, lm555, tps54620, etc.
    
    The endpoint:
    1. Selects the appropriate provider based on manufacturer
    2. Constructs the manufacturer-specific datasheet URL
    3. Downloads the PDF file
    4. Saves it to the local datasheets/{manufacturer}/ directory
    5. Returns the file path and metadata
    
    **URL Formats:**
    - STM: https://www.st.com/resource/en/datasheet/{ic_id}.pdf
    - TI: https://www.ti.com/lit/ds/symlink/{ic_id}.pdf
    """
)
async def download_datasheet(request: DatasheetDownloadRequest):
    """
    Download and store an IC datasheet from the specified manufacturer.
    
    Args:
        request: DatasheetDownloadRequest containing manufacturer and IC ID
        
    Returns:
        DatasheetDownloadResponse with download status and file info
        
    Raises:
        HTTPException: If download fails, IC not found, or manufacturer not supported
    """
    ic_id = request.ic_id
    manufacturer = request.manufacturer
    
    logger.info(f"Received datasheet download request for {manufacturer} IC: {ic_id}")
    
    # Validate IC ID format (basic validation)
    if not ic_id or len(ic_id) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "INVALID_IC_ID",
                "message": "IC ID is too short or invalid",
                "details": {"ic_id": ic_id, "manufacturer": manufacturer}
            }
        )
    
    # Check if datasheet already exists locally
    if datasheet_service.datasheet_exists(ic_id, manufacturer):
        logger.info(f"Datasheet for {manufacturer}/{ic_id} already exists locally")
        existing_info = datasheet_service.get_datasheet_info(ic_id, manufacturer)
        
        return DatasheetDownloadResponse(
            success=True,
            message="Datasheet already exists locally",
            manufacturer=manufacturer,
            ic_id=ic_id,
            file_path=existing_info["file_path"],
            file_size_bytes=existing_info["file_size_bytes"],
            downloaded_at=existing_info["modified_at"]
        )
    
    # Download the datasheet
    try:
        file_path, file_size = await datasheet_service.download_datasheet(ic_id, manufacturer)
        
        return DatasheetDownloadResponse(
            success=True,
            message="Datasheet downloaded successfully",
            manufacturer=manufacturer,
            ic_id=ic_id,
            file_path=str(file_path),
            file_size_bytes=file_size,
            downloaded_at=datetime.utcnow()
        )
    
    except UnsupportedManufacturerException as e:
        logger.error(f"Unsupported manufacturer: {manufacturer}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "UNSUPPORTED_MANUFACTURER",
                "message": str(e),
                "details": {
                    "manufacturer": manufacturer,
                    "supported_manufacturers": datasheet_service.get_supported_manufacturers()
                }
            }
        )
        
    except DatasheetDownloadException as e:
        logger.error(f"Failed to download datasheet for {manufacturer}/{ic_id}: {e}")
        
        # Check if it's a 404 error
        if "404" in str(e) or "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "DATASHEET_NOT_FOUND",
                    "message": str(e),
                    "details": {"ic_id": ic_id, "manufacturer": manufacturer}
                }
            )
        
        # Other download errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "DOWNLOAD_FAILED",
                "message": str(e),
                "details": {"ic_id": ic_id, "manufacturer": manufacturer}
            }
        )
    
    except Exception as e:
        logger.exception(f"Unexpected error downloading datasheet for {manufacturer}/{ic_id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "INTERNAL_ERROR",
                "message": "An unexpected error occurred while downloading the datasheet",
                "details": {"ic_id": ic_id, "manufacturer": manufacturer, "error": str(e)}
            }
        )


@router.get(
    "/check/{manufacturer}/{ic_id}",
    summary="Check if Datasheet Exists Locally",
    description="Check if a datasheet for the given IC ID and manufacturer exists in local storage"
)
async def check_datasheet(manufacturer: str, ic_id: str):
    """
    Check if datasheet exists locally.
    
    Args:
        manufacturer: Manufacturer name (STM, TI, etc.)
        ic_id: IC identifier
        
    Returns:
        Status and file info if exists
    """
    try:
        exists = datasheet_service.datasheet_exists(ic_id, manufacturer)
        
        if exists:
            info = datasheet_service.get_datasheet_info(ic_id, manufacturer)
            return {
                "exists": True,
                "manufacturer": manufacturer,
                "ic_id": ic_id,
                "file_info": info
            }
        else:
            return {
                "exists": False,
                "manufacturer": manufacturer,
                "ic_id": ic_id,
                "message": "Datasheet not found locally"
            }
    except UnsupportedManufacturerException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "UNSUPPORTED_MANUFACTURER",
                "message": str(e),
                "details": {
                    "manufacturer": manufacturer,
                    "supported_manufacturers": datasheet_service.get_supported_manufacturers()
                }
            }
        )


@router.get(
    "/manufacturers",
    summary="Get Supported Manufacturers",
    description="Get list of all supported manufacturers"
)
async def get_supported_manufacturers():
    """
    Get list of supported manufacturers.
    
    Returns:
        List of manufacturer codes and names
    """
    return {
        "manufacturers": datasheet_service.get_supported_manufacturers(),
        "count": len(datasheet_service.get_supported_manufacturers()),
        "details": {
            "STM": {
                "name": "STMicroelectronics",
                "url_pattern": "https://www.st.com/resource/en/datasheet/{ic_id}.pdf",
                "example_ics": ["stm32l031k6", "stm32f407vg", "stm32h743zi"]
            },
            "TI": {
                "name": "Texas Instruments",
                "url_pattern": "https://www.ti.com/lit/ds/symlink/{ic_id}.pdf",
                "example_ics": ["lm358", "lm555", "tps54620"]
            }
        }
    }
