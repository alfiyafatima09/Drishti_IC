"""
Main FastAPI application for IC verification system
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import time

from config.settings import settings
from models.database import init_database
from routes import (
    health,
    video_streaming,
    image_processing,
    ic_verification,
    datasheet_management
)

import os
from logging.handlers import RotatingFileHandler

os.makedirs('logs', exist_ok=True)

log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
log_level = logging.INFO if not settings.debug else logging.DEBUG

file_handler = RotatingFileHandler(
    'logs/app.log',
    maxBytes=10 * 1024 * 1024,  
    backupCount=5
)
file_handler.setLevel(log_level)
file_handler.setFormatter(logging.Formatter(log_format))

console_handler = logging.StreamHandler()
console_handler.setLevel(log_level)
console_handler.setFormatter(logging.Formatter(log_format))

root_logger = logging.getLogger()
root_logger.setLevel(log_level)
root_logger.addHandler(file_handler)
root_logger.addHandler(console_handler)

logger = logging.getLogger(__name__)
logger.info("Logging configured - logs written to logs/app.log")


def create_application() -> FastAPI:
    """Create and configure FastAPI application"""

    init_database()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="AI-powered IC verification system for detecting counterfeit electronic components",
        debug=settings.debug
    )
    
    if settings.debug or "*" in settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origin_regex=r".*",  
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
            expose_headers=["*"],
        )
    else:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
            expose_headers=["*"],
        )

    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        logger.info(
            f"{request.method} {request.url.path} - {response.status_code} - {process_time:.3f}s"
        )
        return response

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"Global exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error", "error": str(exc)}
        )

    app.include_router(health.router, prefix="/api/v1", tags=["health"])
    app.include_router(video_streaming.router, prefix="/api/v1", tags=["video-streaming"])
    app.include_router(image_processing.router, prefix="/api/v1", tags=["image-processing"])
    app.include_router(ic_verification.router, prefix="/api/v1", tags=["ic-verification"])
    app.include_router(datasheet_management.router, prefix="/api/v1", tags=["datasheet-management"])

    @app.options("/{full_path:path}")
    async def options_handler(request: Request):
        """Handle CORS preflight requests"""
        origin = request.headers.get("origin")
        response = JSONResponse(content={})
        if origin:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
            response.headers["Access-Control-Allow-Headers"] = "*"
            response.headers["Access-Control-Max-Age"] = "3600"
        return response

    @app.get("/")
    async def root():
        return {
            "message": f"Welcome to {settings.app_name}",
            "version": settings.app_version,
            "docs": "/docs",
            "redoc": "/redoc"
        }

    return app


app = create_application()
