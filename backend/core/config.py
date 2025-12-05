import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    """Application configuration settings."""
    
    APP_NAME: str = "Drishti IC Backend"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = os.environ.get("DEBUG", False)
    
    # Supabase / database settings
    SUPABASE_URL: str = os.environ.get("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.environ.get("SUPABASE_KEY", "")
    SUPABASE_SERVICE_KEY: str = os.environ.get("SUPABASE_SERVICE_KEY", "")
    DATABASE_URL: str = os.environ.get("DATABASE_URL", "")

    # API Keys
    # GEMINI_API_KEY: str = os.environ.get("GEMINI_API_KEY", "")
    
    # Storage settings
    MEDIA_ROOT: Path = Path(os.environ.get("MEDIA_ROOT", "data"))
    DATASHEET_ROOT: Path = Path(os.environ.get("DATASHEET_ROOT", "data/datasheets"))
    # Backwards compatibility with older code using DATASHEET_FOLDER
    DATASHEET_FOLDER: Path = DATASHEET_ROOT
    
    # Image processing settings
    MAX_IMAGE_SIZE_BYTES: int = int(os.environ.get("MAX_IMAGE_SIZE_BYTES", 50 * 1024 * 1024))
    ALLOWED_IMAGE_TYPES: list[str] = [
        "image/jpeg",
        "image/jpg",
        "image/png",
        "image/bmp",
        "image/tiff",
        "image/heif",
        "image/heic"
    ]
    
    # OCR settings
    OCR_CONFIDENCE_THRESHOLD: float = 70.0
    OCR_MODEL: str = "paddleocr"
    
    # Vision settings
    PIN_DETECTION_MODEL: str = "yolov8"
    
    # Sync settings
    MAX_SCRAPE_RETRIES: int = 3
    SCRAPE_TIMEOUT_SECONDS: int = 5
    AUTO_QUEUE_UNKNOWN: bool = True
    
    # Scan history
    SCAN_HISTORY_RETENTION_DAYS: int = 365
    ENABLE_AUTO_CLEANUP: bool = True

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),  # Check both backend/.env and root/.env
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",  # Ignore extra fields like NEXT_PUBLIC_*
    )


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()

# Ensure directories exist
settings.MEDIA_ROOT.mkdir(parents=True, exist_ok=True)

# Ensure datasheets directory exists
settings.DATASHEET_ROOT.mkdir(parents=True, exist_ok=True)
