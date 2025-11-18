"""
Main entry point for the IC verification FastAPI application
"""
import uvicorn
from core.app import app
from config.settings import settings


if __name__ == "__main__":
    uvicorn.run(
        "core.app:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info" if not settings.debug else "debug"
    )
