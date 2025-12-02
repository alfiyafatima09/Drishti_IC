"""API endpoint routers."""
from backend.api.endpoints.scan import router as scan_router
from backend.api.endpoints.ic import router as ic_router
from backend.api.endpoints.scans_history import router as scans_history_router
from backend.api.endpoints.dashboard import router as dashboard_router
from backend.api.endpoints.queue import router as queue_router
from backend.api.endpoints.fakes import router as fakes_router
from backend.api.endpoints.sync import router as sync_router
from backend.api.endpoints.settings import router as settings_router
from backend.api.endpoints.system import router as system_router
from backend.api.endpoints.camera import router as camera_router

__all__ = [
    "scan_router",
    "ic_router",
    "scans_history_router",
    "dashboard_router",
    "queue_router",
    "fakes_router",
    "sync_router",
    "settings_router",
    "system_router",
    "camera_router",
]

