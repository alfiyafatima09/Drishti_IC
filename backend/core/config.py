from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    """Application configuration settings."""
    
    APP_NAME: str = "Drishti IC Backend"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = False
    
    # Supabase settings
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""  # anon/public key
    SUPABASE_SERVICE_KEY: str = ""  # service role key (for admin operations)
    
    # Database URL (constructed from Supabase or direct PostgreSQL)
    DATABASE_URL: str = ""
    
    # Storage settings
    MEDIA_ROOT: Path = Path("data")
    DATASHEET_ROOT: Path = Path("datasheets")
    DATASHEET_FOLDER: Path = Path("data/datasheets")
    
    # Image processing settings
    MAX_IMAGE_SIZE_BYTES: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_IMAGE_TYPES: list[str] = [
        "image/jpeg",
        "image/jpg",
        "image/png",
        "image/bmp",
        "image/tiff"
    ]
    
    # OCR settings
    OCR_CONFIDENCE_THRESHOLD: float = 70.0
    OCR_MODEL: str = "paddleocr"
    
    # Vision settings
    PIN_DETECTION_MODEL: str = "yolov8"
    
    # Sync settings
    MAX_SCRAPE_RETRIES: int = 3
    SCRAPE_TIMEOUT_SECONDS: int = 30
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
settings.DATASHEET_FOLDER.mkdir(parents=True, exist_ok=True)
