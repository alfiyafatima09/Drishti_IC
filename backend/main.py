from contextlib import asynccontextmanager
import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import logging

from api.endpoints import datasheets
from api.endpoints import digikey as digikey_router
from core.config import settings
from core.database import init_db
from api.endpoints import (
    scan_router,
    ic_router,
    scans_history_router,
    dashboard_router,
    queue_router,
    fakes_router,
    sync_router,
    settings_router,
    system_router,
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
    websockets,
)
from api.endpoints import images, datasheets, ic_analysis

STATIC_DIR = Path(__file__).parent / "static"

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
    
    yield

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
    Backend APIs for Drishti IC
    """,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
app.include_router(websockets.router)
app.include_router(images.router)
app.include_router(datasheets.router)
# app.include_router(ic_analysis.router)
app.include_router(digikey_router.router)


@app.get("/", tags=["Root"])
async def root():   
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs",
    }


@app.get("/camera", tags=["Camera"], include_in_schema=False)
async def camera_page():
    """Serve the phone camera streaming page."""
    camera_html = STATIC_DIR / "camera.html"
    if camera_html.exists():
        return FileResponse(camera_html, media_type="text/html")
    return {"error": "Camera page not found"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        # host="0.0.0.0",  # Bind to all interfaces for network access
        port=int(os.environ.get("PORT", 8000)),
    )
