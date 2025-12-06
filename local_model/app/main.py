# Main FastAPI application entry point with CORS and Router configuration
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routers import chat, vision, health

app = FastAPI(title=settings.TITLE, version=settings.VERSION)

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routers
app.include_router(chat.router, prefix="/api", tags=["chat"])
app.include_router(vision.router, prefix="/api", tags=["vision"])
app.include_router(health.router, tags=["health"])

@app.get("/")
def root():
    return {"status": "online", "model": settings.MODEL_NAME}
