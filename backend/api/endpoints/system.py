"""System endpoints - Health and status checks."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from pathlib import Path
import logging
import socket

from backend.core.database import get_db, check_db_connection
from backend.core.config import settings
from backend.services import ICService, QueueService, SyncService
from backend.schemas import (
    HealthResponse,
    SystemStatusResponse,
    DatabaseStatus,
    CameraStatus,
    StorageStatus,
    LastSyncInfo,
    SyncStatus,
)
from backend.schemas.system import NetworkStatus, QueueStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["System"])

# Track camera connection (in-memory)
_camera_connected = False
_last_frame_at = None


def set_camera_status(connected: bool, frame_time: datetime = None):
    """Update camera status (called from WebSocket handler)."""
    global _camera_connected, _last_frame_at
    _camera_connected = connected
    if frame_time:
        _last_frame_at = frame_time


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Basic health check endpoint.
    """
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow(),
    )


@router.get("/system/status", response_model=SystemStatusResponse)
async def get_system_status(
    db: AsyncSession = Depends(get_db),
):
    """
    Comprehensive system status.
    
    Includes database, camera, network, queue, and storage status.
    """
    # Check database
    db_connected = await check_db_connection()
    ic_count = 0
    if db_connected:
        ic_count = await ICService.get_count(db)
    
    # Check network (try to resolve DNS)
    internet_available = False
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=3)
        internet_available = True
    except OSError:
        pass
    
    # Get queue status
    queue_items, pending_count, failed_count = await QueueService.list_queue(db)
    
    # Get storage info
    datasheet_folder = settings.DATASHEET_FOLDER
    datasheet_count = 0
    folder_size_mb = 0.0
    
    if datasheet_folder.exists():
        pdf_files = list(datasheet_folder.glob("*.pdf"))
        datasheet_count = len(pdf_files)
        folder_size_mb = sum(f.stat().st_size for f in pdf_files) / (1024 * 1024)
    
    # Get last sync info
    sync_history, _ = await SyncService.get_history(db, limit=1)
    last_sync = None
    if sync_history:
        last_job = sync_history[0]
        last_sync = LastSyncInfo(
            job_id=last_job.job_id,
            status=SyncStatus(last_job.status),
            completed_at=last_job.completed_at,
        )
    
    # Determine overall status
    overall_status = "operational"
    if not db_connected:
        overall_status = "offline"
    elif not _camera_connected:
        overall_status = "degraded"
    
    return SystemStatusResponse(
        status=overall_status,
        database=DatabaseStatus(
            connected=db_connected,
            ic_count=ic_count,
        ),
        camera=CameraStatus(
            connected=_camera_connected,
            last_frame_at=_last_frame_at,
        ),
        network=NetworkStatus(
            internet_available=internet_available,
            last_checked=datetime.utcnow(),
        ),
        queue=QueueStatus(
            pending_count=pending_count,
            failed_count=failed_count,
        ),
        storage=StorageStatus(
            datasheet_folder=str(datasheet_folder),
            datasheet_count=datasheet_count,
            folder_size_mb=round(folder_size_mb, 2),
        ),
        last_sync=last_sync,
    )

