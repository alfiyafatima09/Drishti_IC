"""
BEL IC Verification System - Main Application Entry Point

This is an offline-first API for counterfeit IC detection.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from backend.core.config import settings
from backend.core.database import init_db
from backend.api.endpoints import (
    scan_router,
    ic_router,
    scans_history_router,
    dashboard_router,
    queue_router,
    fakes_router,
    sync_router,
    settings_router,
    system_router,
    camera_router,
)

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle manager."""
    # Startup
    logger.info("Starting BEL IC Verification System...")
    
    # Initialize database (create tables if not exist)
    try:
        await init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        # Don't fail startup - DB might not be configured yet
    
    yield
    
    # Shutdown
    logger.info("Shutting down BEL IC Verification System...")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
    ## BEL IC Verification System
    
    Offline-first API for counterfeit IC detection using computer vision.
    
    ### Features
    - **OCR + Vision**: Read chip text and count pins
    - **Golden Record**: Verify against local database
    - **Self-Healing**: Automatically queue unknown ICs for sync
    - **Fake Registry**: Track known counterfeit part numbers
    - **Weekly Sync**: Update database when internet is available
    
    ### Scan Flow
    1. Upload image → `/api/v1/scan`
    2. If PARTIAL (BTC component) → flip and upload → `/api/v1/scan/{id}/bottom`
    3. If UNKNOWN → manual override available → `/api/v1/scan/override`
    """,
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all routers
app.include_router(scan_router)
app.include_router(ic_router)
app.include_router(scans_history_router)
app.include_router(dashboard_router)
app.include_router(queue_router)
app.include_router(fakes_router)
app.include_router(sync_router)
app.include_router(settings_router)
app.include_router(system_router)
app.include_router(camera_router)


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint - API information."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs",
        "redoc": "/redoc",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
    )
