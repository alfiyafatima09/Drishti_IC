"""Settings endpoints - System configuration management."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
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

