from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend_stem.api.endpoints import images
from backend_stem.core.config import settings

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="IC Verification and Analysis System"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(images.router)


@app.get("/", tags=["health"])
def root():
    """Root endpoint - API health check."""
    return {
        "message": "Drishti IC API is running",
        "version": settings.APP_VERSION,
        "status": "healthy"
    }