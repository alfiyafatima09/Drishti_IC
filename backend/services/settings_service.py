"""Service for application settings operations."""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, Any
import logging
import json

from core.config import settings
from models import AppSettings

logger = logging.getLogger(__name__)

# Default settings
DEFAULT_SETTINGS = {
    "datasheet_folder_path": (settings.DATASHEET_FOLDER, "STRING"),
    "auto_queue_unknown": ("true", "BOOLEAN"),
    "ocr_confidence_threshold": ("70.0", "FLOAT"),
    "scan_history_retention_days": ("365", "INTEGER"),
    "enable_auto_cleanup": ("true", "BOOLEAN"),
    "pin_detection_model": ("yolov8", "STRING"),
    "ocr_model": ("paddleocr", "STRING"),
    "max_scrape_retries": ("3", "INTEGER"),
    "scrape_timeout_seconds": ("5", "INTEGER"),
}


class SettingsService:
    """Service for managing application settings."""

    @staticmethod
    async def get_all(db: AsyncSession) -> dict[str, Any]:
        """Get all settings as a dictionary."""
        result = await db.execute(select(AppSettings))
        settings = result.scalars().all()
        
        # Build settings dict
        settings_dict = {}
        for setting in settings:
            settings_dict[setting.key] = setting.get_typed_value()
        
        # Add defaults for any missing settings
        for key, (default_value, value_type) in DEFAULT_SETTINGS.items():
            if key not in settings_dict:
                # Create the missing setting
                new_setting = AppSettings(
                    key=key,
                    value=default_value,
                    value_type=value_type,
                )
                db.add(new_setting)
                settings_dict[key] = new_setting.get_typed_value()
        
        await db.flush()
        return settings_dict

    @staticmethod
    async def get(db: AsyncSession, key: str) -> Optional[Any]:
        """Get a single setting value."""
        result = await db.execute(
            select(AppSettings).where(AppSettings.key == key)
        )
        setting = result.scalar_one_or_none()
        
        if setting:
            return setting.get_typed_value()
        
        # Return default if exists
        if key in DEFAULT_SETTINGS:
            return DEFAULT_SETTINGS[key][0]
        
        return None

    @staticmethod
    async def update(
        db: AsyncSession,
        updates: dict[str, Any],
        updated_by: Optional[str] = None,
    ) -> dict[str, Any]:
        """Update multiple settings."""
        updated = {}
        
        for key, value in updates.items():
            # Get existing setting
            result = await db.execute(
                select(AppSettings).where(AppSettings.key == key)
            )
            setting = result.scalar_one_or_none()
            
            if setting:
                # Determine value type
                if isinstance(value, bool):
                    setting.value = str(value).lower()
                    setting.value_type = "BOOLEAN"
                elif isinstance(value, int):
                    setting.value = str(value)
                    setting.value_type = "INTEGER"
                elif isinstance(value, float):
                    setting.value = str(value)
                    setting.value_type = "FLOAT"
                elif isinstance(value, (dict, list)):
                    setting.value = json.dumps(value)
                    setting.value_type = "JSON"
                else:
                    setting.value = str(value)
                    setting.value_type = "STRING"
                
                if updated_by:
                    setting.updated_by = updated_by
                
                updated[key] = value
                logger.info(f"Updated setting '{key}' to '{value}'")
            else:
                # Create new setting
                value_type = "STRING"
                str_value = str(value)
                
                if isinstance(value, bool):
                    str_value = str(value).lower()
                    value_type = "BOOLEAN"
                elif isinstance(value, int):
                    value_type = "INTEGER"
                elif isinstance(value, float):
                    value_type = "FLOAT"
                elif isinstance(value, (dict, list)):
                    str_value = json.dumps(value)
                    value_type = "JSON"
                
                new_setting = AppSettings(
                    key=key,
                    value=str_value,
                    value_type=value_type,
                    updated_by=updated_by,
                )
                db.add(new_setting)
                updated[key] = value
                logger.info(f"Created setting '{key}' with value '{value}'")
        
        await db.flush()
        return updated

    @staticmethod
    async def get_datasheet_folder(db: AsyncSession) -> str:
        """Convenience method to get datasheet folder path."""
        value = await SettingsService.get(db, "datasheet_folder_path")
        return value or settings.DATASHEET_FOLDER

    @staticmethod
    async def should_auto_queue(db: AsyncSession) -> bool:
        """Convenience method to check if auto-queue is enabled."""
        value = await SettingsService.get(db, "auto_queue_unknown")
        if isinstance(value, bool):
            return value
        return str(value).lower() in ("true", "1", "yes")

