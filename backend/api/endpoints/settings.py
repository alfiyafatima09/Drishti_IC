"""Settings endpoints - System configuration management."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
import logging

from core.database import get_db
from services import SettingsService
from schemas import (
    SettingsResponse,
    SettingsUpdateRequest,
    SettingsUpdateResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/settings", tags=["Settings"])


class DimensionCalibrationRequest(BaseModel):
    """Request to calibrate dimension measurement."""
    known_dimension_mm: float = Field(..., description="The known real dimension in millimeters (e.g., 19.3 for LM324N width)")
    measured_pixels: float = Field(..., description="The measured pixel dimension from the image")


class DimensionCalibrationResponse(BaseModel):
    """Response from dimension calibration."""
    success: bool
    message: str
    mm_per_pixel: float = Field(..., description="Calculated mm per pixel ratio")
    example_conversions: dict = Field(..., description="Example conversions for verification")


@router.get("/list", response_model=SettingsResponse)
async def list_settings(
    db: AsyncSession = Depends(get_db),
):
    """
    Get all system settings.
    """
    settings = await SettingsService.get_all(db)
    return SettingsResponse(settings=settings)


@router.patch("/update", response_model=SettingsUpdateResponse)
async def update_settings(
    request: dict,  # Accept any dict
    db: AsyncSession = Depends(get_db),
):
    """
    Update one or more system settings.
    
    Pass key-value pairs of settings to update.
    """
    if not request:
        return SettingsUpdateResponse(
            success=False,
            message="No settings provided to update.",
            updated_settings={},
        )
    
    updated = await SettingsService.update(db, request)
    
    return SettingsUpdateResponse(
        success=True,
        message="Settings updated successfully.",
        updated_settings=updated,
    )


@router.post("/calibrate-dimensions", response_model=DimensionCalibrationResponse)
async def calibrate_dimensions(
    request: DimensionCalibrationRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Calibrate the dimension measurement system.
    
    **How to use:**
    1. Take a scan of an IC with KNOWN dimensions (e.g., LM324N is 19.3mm x 7.1mm)
    2. Look at the pixel dimensions returned in the scan result (width_px, height_px)
    3. Call this endpoint with the known real dimension and the measured pixels
    
    **Example for LM324N (DIP-14):**
    - Real width: 19.3 mm
    - If the scan shows width_px = 237, then:
      - known_dimension_mm = 19.3
      - measured_pixels = 237
    
    This will calculate and save the correct mm_per_pixel ratio.
    
    **Alternative: Use pin pitch**
    - DIP pin pitch = 2.54 mm
    - Measure pixels between two adjacent pins
    - known_dimension_mm = 2.54
    - measured_pixels = (pixels between pins)
    """
    if request.measured_pixels <= 0:
        return DimensionCalibrationResponse(
            success=False,
            message="measured_pixels must be greater than 0",
            mm_per_pixel=0,
            example_conversions={}
        )
    
    if request.known_dimension_mm <= 0:
        return DimensionCalibrationResponse(
            success=False,
            message="known_dimension_mm must be greater than 0",
            mm_per_pixel=0,
            example_conversions={}
        )
    
    # Calculate mm_per_pixel
    mm_per_pixel = request.known_dimension_mm / request.measured_pixels
    
    # Save to settings
    await SettingsService.update(db, {"dimension_mm_per_pixel": mm_per_pixel})
    
    logger.info(f"Dimension calibration updated: mm_per_pixel = {mm_per_pixel:.6f}")
    
    # Provide example conversions for verification
    example_conversions = {
        "100_pixels": round(100 * mm_per_pixel, 2),
        "200_pixels": round(200 * mm_per_pixel, 2),
        "500_pixels": round(500 * mm_per_pixel, 2),
        "1000_pixels": round(1000 * mm_per_pixel, 2),
    }
    
    return DimensionCalibrationResponse(
        success=True,
        message=f"Calibration successful! mm_per_pixel = {mm_per_pixel:.6f}",
        mm_per_pixel=round(mm_per_pixel, 6),
        example_conversions=example_conversions
    )


@router.get("/dimension-calibration")
async def get_dimension_calibration(
    db: AsyncSession = Depends(get_db),
):
    """
    Get current dimension calibration value.
    """
    mm_per_pixel = await SettingsService.get(db, "dimension_mm_per_pixel")
    
    if mm_per_pixel and float(mm_per_pixel) > 0:
        return {
            "calibrated": True,
            "mm_per_pixel": float(mm_per_pixel),
            "message": "Dimension measurement is calibrated"
        }
    else:
        return {
            "calibrated": False,
            "mm_per_pixel": 0,
            "message": "Not calibrated. Use /calibrate-dimensions endpoint to calibrate."
        }

