"""API endpoint routers."""
from api.endpoints.scan import router as scan_router
from api.endpoints.ic import router as ic_router
from api.endpoints.scans_history import router as scans_history_router
from api.endpoints.dashboard import router as dashboard_router
from api.endpoints.queue import router as queue_router
from api.endpoints.fakes import router as fakes_router
from api.endpoints.sync import router as sync_router
from api.endpoints.settings import router as settings_router
from api.endpoints.system import router as system_router
from api.endpoints.camera import router as camera_router

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

