from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application configuration settings."""
    
    APP_NAME: str = "Drishti IC Backend"
    APP_VERSION: str = "0.1.0"
    
    # API Keys
    GEMINI_API_KEY: str = ""
    
    # Storage settings
    MEDIA_ROOT: Path = Path("media")
    DATASHEET_ROOT: Path = Path("datasheets")
    
    # Image processing settings
    MAX_IMAGE_SIZE_BYTES: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_IMAGE_TYPES: list[str] = [
        "image/jpeg",
        "image/jpg",
        "image/png",
        "image/bmp",
        "image/tiff"
    ]
    
    # Preprocessing defaults
    DEFAULT_DENOISE: bool = True
    DEFAULT_NORMALIZE: bool = True
    DEFAULT_ENHANCE_CONTRAST: bool = False
    DEFAULT_EDGE_PREP: bool = False

    class Config:
        env_file = ".env"


settings = Settings()

# Ensure media directory exists
settings.MEDIA_ROOT.mkdir(parents=True, exist_ok=True)

# Ensure datasheets directory exists
settings.DATASHEET_ROOT.mkdir(parents=True, exist_ok=True)
