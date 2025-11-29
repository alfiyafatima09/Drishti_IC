"""
Application settings and configuration
"""
import os
from typing import List, Dict, Any
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # API Configuration
    app_name: str = "Drishti IC Verification API"
    app_version: str = "1.0.0"
    debug: bool = Field(default=True, env="DEBUG")  # Default to True for development

    # Server Configuration
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")

    # CORS Configuration
    cors_origins: List[str] = Field(default=["*"], env="CORS_ORIGINS")

    # Database Configuration
    database_url: str = Field(default="sqlite:///../../data.sqlite", env="DATABASE_URL")

    # External API Keys
    roboflow_api_key: str = Field(default="", env="ROBOFLOW_API_KEY")

    # OCR Configuration
    tesseract_cmd: str = Field(default="/usr/local/bin/tesseract", env="TESSERACT_CMD")

    # Image Processing Configuration
    max_image_size: int = Field(default=10 * 1024 * 1024, env="MAX_IMAGE_SIZE")  # 10MB
    supported_image_formats: List[str] = Field(default=["jpg", "jpeg", "png", "bmp", "tiff"])

    # Video Streaming Configuration
    video_chunk_size: int = Field(default=8192, env="VIDEO_CHUNK_SIZE")
    max_video_duration: int = Field(default=300, env="MAX_VIDEO_DURATION")  # 5 minutes

    # Datasheet Configuration
    datasheet_cache_dir: str = Field(default="./cache/datasheets", env="DATASHEET_CACHE_DIR")
    datasheet_timeout: int = Field(default=30, env="DATASHEET_TIMEOUT")  # seconds

    # Logo Detection Configuration
    sift_nfeatures: int = Field(default=500, env="SIFT_NFEATURES")
    logo_match_threshold: float = Field(default=0.7, env="LOGO_MATCH_THRESHOLD")

    # Font Analysis Configuration
    font_similarity_threshold: float = Field(default=0.85, env="FONT_SIMILARITY_THRESHOLD")

    # Supported Manufacturers
    supported_manufacturers: Dict[str, Dict[str, Any]] = Field(default={
        "STMicroelectronics": {
            "short_name": "STM",
            "website": "https://www.st.com",
            "datasheet_base_url": "https://www.st.com/resource/en/datasheet"
        },
        "Texas Instruments": {
            "short_name": "TI",
            "website": "https://www.ti.com",
            "datasheet_base_url": "https://www.ti.com/lit/ds"
        },
        "NXP": {
            "short_name": "NXP",
            "website": "https://www.nxp.com",
            "datasheet_base_url": "https://www.nxp.com/docs/en/data-sheet"
        },
        "Microchip": {
            "short_name": "MICROCHIP",
            "website": "https://www.microchip.com",
            "datasheet_base_url": "https://ww1.microchip.com/downloads/en/DeviceDoc"
        },
        "Infineon": {
            "short_name": "INFINEON",
            "website": "https://www.infineon.com",
            "datasheet_base_url": "https://www.infineon.com/dgdl"
        },
        "Analog Devices": {
            "short_name": "ADI",
            "website": "https://www.analog.com",
            "datasheet_base_url": "https://www.analog.com/media/en/technical-documentation/data-sheets"
        },
        "ON Semiconductor": {
            "short_name": "ONSEMI",
            "website": "https://www.onsemi.com",
            "datasheet_base_url": "https://www.onsemi.com/pub/Collateral"
        }
    })

    # Verification Metrics Configuration
    verification_thresholds: Dict[str, float] = Field(default={
        "logo_match": 0.8,
        "font_similarity": 0.85,
        "marking_accuracy": 0.9,
        "overall_confidence": 0.75
    })

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
