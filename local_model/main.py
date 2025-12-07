from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1.vision import router as vision_router

app = FastAPI(title="Local Model API", version="1.0.0")

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(vision_router, prefix="/api/v1", tags=["Vision"])

@app.get("/")
def health_check():
    return {"status": "ok", "model": settings.MODEL_NAME}
