import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


# Get the backend directory (where this file is located)
BACKEND_DIR = Path(__file__).parent.parent.resolve()
# Project root is one level up from backend
PROJECT_ROOT = BACKEND_DIR.parent


class Settings(BaseSettings):
    """Application configuration settings."""
    
    APP_NAME: str = "Drishti IC Backend"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = os.environ.get("DEBUG", False)
    
    SUPABASE_URL: str = os.environ.get("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.environ.get("SUPABASE_KEY", "")
    SUPABASE_SERVICE_KEY: str = os.environ.get("SUPABASE_SERVICE_KEY", "")
    DATABASE_URL: str = os.environ.get("DATABASE_URL", "")

    GEMINI_API_KEY: str = os.environ.get("GEMINI_API_KEY", "AIzaSyDxHomY9cWMZMT9ZklyV3RMR8AbhZ5igE0")
    
    # Use absolute paths based on project root
    # Handle both absolute and relative paths in env vars
    @property
    def MEDIA_ROOT(self) -> Path:
        env_path = os.environ.get("MEDIA_ROOT", "")
        if env_path:
            p = Path(env_path)
            return p if p.is_absolute() else PROJECT_ROOT / p
        return PROJECT_ROOT / "media"
    
    @property
    def DATASHEET_FOLDER(self) -> Path:
        env_path = os.environ.get("DATASHEET_ROOT", "")
        if env_path:
            p = Path(env_path)
            return p if p.is_absolute() else PROJECT_ROOT / p
        return PROJECT_ROOT / "datasheets"
    
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
    
    OCR_CONFIDENCE_THRESHOLD: float = 70.0
    OCR_MODEL: str = "paddleocr"
    
    PIN_DETECTION_MODEL: str = "yolov8"
    
    MAX_SCRAPE_RETRIES: int = 3
    SCRAPE_TIMEOUT_SECONDS: int = 30  # Increased for PDF downloads
    AUTO_QUEUE_UNKNOWN: bool = True
    
    # Scan history
    SCAN_HISTORY_RETENTION_DAYS: int = 365
    ENABLE_AUTO_CLEANUP: bool = True

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",  
    )

    DIGIKEY_CLIENT_ID: str = os.environ.get("DIGIKEY_CLIENT_ID", "")
    DIGIKEY_CLIENT_SECRET: str = os.environ.get("DIGIKEY_CLIENT_SECRET", "")
    DIGIKEY_TOKEN_URL: str = os.environ.get("DIGIKEY_TOKEN_URL", "https://api.digikey.com/v1/oauth2/token")
    DIGIKEY_SEARCH_URL: str = os.environ.get("DIGIKEY_SEARCH_URL", "https://api.digikey.com/products/v4/search/keyword")


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()

settings.MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
settings.DATASHEET_FOLDER.mkdir(parents=True, exist_ok=True)
