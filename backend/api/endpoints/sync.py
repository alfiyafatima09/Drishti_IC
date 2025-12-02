"""Sync endpoints - Weekly sync job management."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from core.database import get_db
from services import SyncService, QueueService
from schemas import (
    SyncStartRequest,
    SyncJobInfo,
    SyncStatusResponse,
    SyncHistoryResult,
    SyncHistoryItem,
    SuccessResponse,
    SyncStatus,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/sync", tags=["Sync Operations"])


@router.post("/start", response_model=SyncJobInfo, status_code=202)
async def start_sync(
    request: SyncStartRequest = SyncStartRequest(),
    db: AsyncSession = Depends(get_db),
):
    """
    Start weekly sync job.
    
    Triggers background scraping for all queued ICs.
    Requires internet connection.
    """
    try:
        job = await SyncService.start_sync(
            db=db,
            max_items=request.max_items,
            retry_failed=request.retry_failed,
        )
        
        # Estimate time (roughly 2 minutes per item)
        estimated_minutes = job.total_items * 2 if job.total_items else 0
        
        return SyncJobInfo(
            job_id=job.job_id,
            status=SyncStatus.PROCESSING,
            message=f"Sync job started successfully. Processing {job.total_items} items.",
            queue_size=job.total_items,
            estimated_time_minutes=estimated_minutes,
        )
    except ValueError as e:
        # Job already running
        active = await SyncService.get_active_job(db)
        raise HTTPException(
            status_code=409,
            detail={
                "error": "SYNC_IN_PROGRESS",
                "message": str(e),
                "current_job_id": str(active.job_id) if active else None,
                "progress_percentage": active._calculate_progress() if active else 0,
            }
        )


@router.get("/status", response_model=SyncStatusResponse)
async def get_sync_status(
    db: AsyncSession = Depends(get_db),
):
    """
    Get current sync job status.
    
    Poll this endpoint to update the progress bar.
    """
    status = await SyncService.get_status(db)
    
    return SyncStatusResponse(
        job_id=status.get("job_id"),
        status=SyncStatus(status["status"]),
        progress_percentage=status.get("progress_percentage", 0),
        current_item=status.get("current_item"),
        total_items=status.get("total_items", 0),
        processed_items=status.get("processed_items", 0),
        success_count=status.get("success_count", 0),
        failed_count=status.get("failed_count", 0),
        fake_count=status.get("fake_count", 0),
        started_at=status.get("started_at"),
        estimated_completion=status.get("estimated_completion"),
        message=status.get("message"),
    )


@router.post("/cancel", response_model=SuccessResponse)
async def cancel_sync(
    db: AsyncSession = Depends(get_db),
):
    """
    Cancel running sync job.
    """
    job = await SyncService.cancel_sync(db)
    
    if not job:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "NO_ACTIVE_JOB",
                "message": "No sync job is currently running.",
            }
        )
    
    return SuccessResponse(
        success=True,
        message=f"Sync job cancelled. {job.processed_items} of {job.total_items} items were processed.",
    )


@router.get("/history", response_model=SyncHistoryResult)
async def get_sync_history(
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
):
    """
    Get past sync job results.
    """
    jobs, total_count = await SyncService.get_history(db, limit=limit)
    
    return SyncHistoryResult(
        sync_jobs=[
            SyncHistoryItem(
                job_id=job.job_id,
                status=SyncStatus(job.status),
                started_at=job.started_at,
                completed_at=job.completed_at,
                total_items=job.total_items,
                success_count=job.success_count,
                failed_count=job.failed_count,
                fake_count=job.fake_count,
            )
            for job in jobs
        ],
        total_count=total_count,
    )

