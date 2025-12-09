"""Sync endpoints - Weekly sync job management."""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
import logging
import asyncio

from core.database import get_db, get_db_for_background
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


async def run_sync_background(job_id):
    """Background task wrapper for sync processing."""
    # Get a fresh database session for background task
    async for db in get_db_for_background():
        try:
            await SyncService.run_sync_job(db, job_id)
        except Exception as e:
            logger.exception(f"Background sync failed: {e}")
        finally:
            await db.close()


@router.post("/start", response_model=SyncJobInfo, status_code=202)
async def start_sync(
    background_tasks: BackgroundTasks,
    request: SyncStartRequest = SyncStartRequest(),
    db: AsyncSession = Depends(get_db),
):
    """
    Start sync job with optional filters.
    
    Triggers background scraping for queued ICs matching the filter criteria.
    Requires internet connection.
    
    If a sync job is already running, it will be cancelled immediately and a new one will start.
    
    Parameters:
    - max_items: Limit how many items to process
    - retry_failed: Whether to retry previously failed items
    - status_filter: Only sync items with these statuses (e.g., ["PENDING", "FAILED"])
    
    Flow:
    1. Downloads datasheet PDF for each queued IC
    2. Parses PDF and extracts IC specifications
    3. Stores specs in ic_specifications table
    4. Removes successfully processed items from queue
    5. After 3 failed attempts, moves item to fake registry
    """
    # Check if there's an active job and cancel it if exists
    active = await SyncService.get_active_job(db)
    if active:
        logger.info(f"Cancelling existing sync job {active.job_id} to start new one")
        await SyncService.cancel_sync(db)
        # Wait a bit for the cancellation to take effect
        await asyncio.sleep(0.5)
    
    # Now start the new sync job
    job = await SyncService.start_sync(
        db=db,
        max_items=request.max_items,
        retry_failed=request.retry_failed,
        status_filter=request.status_filter,
    )
    
    # Commit the job creation
    await db.commit()
    
    # Start background processing
    background_tasks.add_task(run_sync_background, job.job_id)
    
    # Estimate time (roughly 5 seconds per item for download + parse)
    estimated_minutes = max(1, (job.total_items * 5) // 60)
    
    status_msg = ""
    if request.status_filter:
        status_msg = f" (filtering by: {', '.join(request.status_filter)})"
    
    cancelled_msg = " (previous job cancelled)" if active else ""
    
    return SyncJobInfo(
        job_id=job.job_id,
        status=SyncStatus.PROCESSING,
        message=f"Sync job started successfully{cancelled_msg}. Processing {job.total_items} items{status_msg}.",
        queue_size=job.total_items,
        estimated_time_minutes=estimated_minutes,
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
    Cancel running sync job immediately.
    
    The job will be stopped immediately and marked as cancelled.
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
        message=f"Sync job cancelled immediately. {job.processed_items} of {job.total_items} items were processed.",
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
