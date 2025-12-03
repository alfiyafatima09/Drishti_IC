"""
Datasheet Management API endpoints.
Matches the API contract defined in contracts/openapi.yaml
"""
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.responses import JSONResponse
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from schemas.datasheets import (
    DatasheetDownloadRequest,
    DatasheetDownloadResponse,
    ManufacturerListResponse,
    ErrorResponse,
)
from services.datasheet import (
    datasheet_service,
    DatasheetDownloadException,
    UnsupportedManufacturerException,
)
from core.database import get_db
from core.constants import get_supported_manufacturers, get_manufacturer_details

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/datasheets",
    tags=["Datasheet Management"],
    responses={
        400: {"model": ErrorResponse, "description": "Bad Request"},
        404: {"model": ErrorResponse, "description": "Datasheet Not Found"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"}
    }
)


@router.post(
    "/download",
    response_model=DatasheetDownloadResponse,
    status_code=status.HTTP_200_OK,
    summary="Download Datasheet from Manufacturer",
    description=f"""
    Download IC datasheet from manufacturer websites and extract data.
    
    Supported Manufacturers:
    {', '.join(f'{m}' for m in get_supported_manufacturers())}
    """
)
async def download_datasheet(
    request: DatasheetDownloadRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Download and store an IC datasheet from the specified manufacturer(s).
    
    Args:
        request: DatasheetDownloadRequest containing part_number and optional manufacturer
        db: Database session
        
    Returns:
        DatasheetDownloadResponse with download status and results
        
    Raises:
        HTTPException: If request is invalid or manufacturer not supported
    """
    part_number = request.part_number.strip()
    manufacturer = request.manufacturer.upper().strip() if request.manufacturer else None
    
    logger.info(
        f"Received datasheet download request for part_number={part_number}, "
        f"manufacturer={manufacturer or 'ALL'}"
    )
        
    if not part_number or len(part_number) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "INVALID_PART_NUMBER",
                "message": "Part number is required and must be at least 2 characters",
                "details": {
                    "provided": part_number,
                    "min_length": 2
                }
            }
        )
    
    if manufacturer:
        from core.constants import is_valid_manufacturer
        if not is_valid_manufacturer(manufacturer):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "INVALID_MANUFACTURER",
                    "message": f"Manufacturer '{manufacturer}' is not supported",
                    "details": {
                        "provided": manufacturer,
                        "supported_manufacturers": get_supported_manufacturers()
                    }
                }
            )
    
    try:
        result = await datasheet_service.download_datasheet(
            part_number=part_number,
            manufacturer_code=manufacturer,
            db=db
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "DATASHEET_NOT_FOUND",
                    "message": f"No datasheet found for '{part_number}' on any supported manufacturer",
                    "details": {
                        "part_number": part_number,
                        "manufacturers_tried": result["manufacturers_tried"]
                    }
                }
            )
        
        return DatasheetDownloadResponse(**result)
        
    except UnsupportedManufacturerException as e:
        logger.error(f"Unsupported manufacturer: {manufacturer}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "INVALID_MANUFACTURER",
                "message": str(e),
                "details": {
                    "manufacturer": manufacturer,
                    "supported_manufacturers": get_supported_manufacturers()
                }
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error downloading datasheet for {part_number}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "INTERNAL_ERROR",
                "message": "An unexpected error occurred while downloading the datasheet",
                "details": {
                    "part_number": part_number,
                    "manufacturer": manufacturer,
                    "error": str(e)
                }
            }
        )


@router.get(
    "/manufacturers",
    response_model=ManufacturerListResponse,
    summary="List Supported Manufacturers",
    description="""
    Get list of all supported manufacturers for datasheet downloads.
    Returns enum values and detailed information for each.
    """
)
async def list_manufacturers():
    """
    Get list of supported manufacturers.
    
    Returns:
        ManufacturerListResponse with manufacturer codes and details
    """
    manufacturers = get_supported_manufacturers()
    details = get_manufacturer_details()
    
    return ManufacturerListResponse(
        manufacturers=manufacturers,
        count=len(manufacturers),
        details=details
    )
