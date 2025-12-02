"""Service for sync job operations."""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
from datetime import datetime
from uuid import UUID
import logging
import asyncio

from models import SyncJob, DatasheetQueue
from services.queue_service import QueueService
from services.fake_service import FakeService
from services.ic_service import ICService
from schemas import ICSpecificationCreate

logger = logging.getLogger(__name__)


class SyncService:
    """Service for managing weekly sync operations."""

    # Track active job (simple in-memory tracking)
    _active_job_id: Optional[UUID] = None

    @staticmethod
    async def get_active_job(db: AsyncSession) -> Optional[SyncJob]:
        """Get the currently running sync job if any."""
        result = await db.execute(
            select(SyncJob).where(SyncJob.status == "PROCESSING")
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def start_sync(
        db: AsyncSession,
        max_items: Optional[int] = None,
        retry_failed: bool = True,
    ) -> SyncJob:
        """Start a new sync job."""
        # Check if already running
        active = await SyncService.get_active_job(db)
        if active:
            raise ValueError("A sync job is already running")

        # Get items to process
        pending_items = await QueueService.get_pending_items(db, limit=max_items)
        
        if retry_failed:
            failed_items = await QueueService.get_failed_items(db)
            # Combine, prioritizing pending
            all_items = pending_items + [f for f in failed_items if f not in pending_items]
        else:
            all_items = pending_items

        if max_items:
            all_items = all_items[:max_items]

        # Create sync job
        job = SyncJob(
            status="PROCESSING",
            started_at=datetime.utcnow(),
            total_items=len(all_items),
            processed_items=0,
            success_count=0,
            failed_count=0,
            fake_count=0,
            log=[],
        )
        db.add(job)
        await db.flush()
        await db.refresh(job)

        SyncService._active_job_id = job.job_id
        logger.info(f"Started sync job {job.job_id} with {len(all_items)} items")

        return job

    @staticmethod
    async def get_status(db: AsyncSession) -> dict:
        """Get current sync status."""
        active = await SyncService.get_active_job(db)
        
        if active:
            return active.to_dict()
        
        # Return idle status with queue info
        queue_size = await QueueService.get_queue_size(db)
        return {
            "job_id": None,
            "status": "IDLE",
            "progress_percentage": 0,
            "current_item": None,
            "total_items": 0,
            "processed_items": 0,
            "success_count": 0,
            "failed_count": 0,
            "fake_count": 0,
            "started_at": None,
            "estimated_completion": None,
            "message": f"No sync job running. Queue has {queue_size} pending items.",
        }

    @staticmethod
    async def cancel_sync(db: AsyncSession) -> Optional[SyncJob]:
        """Cancel the running sync job."""
        active = await SyncService.get_active_job(db)
        if not active:
            return None

        active.status = "CANCELLED"
        active.completed_at = datetime.utcnow()
        active.error_message = f"Cancelled. {active.processed_items} of {active.total_items} items processed."

        SyncService._active_job_id = None

        await db.flush()
        await db.refresh(active)
        logger.info(f"Cancelled sync job {active.job_id}")
        return active

    @staticmethod
    async def get_history(
        db: AsyncSession, limit: int = 10
    ) -> tuple[list[SyncJob], int]:
        """Get sync job history."""
        # Get completed jobs (not IDLE or PROCESSING)
        result = await db.execute(
            select(SyncJob).where(
                SyncJob.status.in_(["COMPLETED", "ERROR", "CANCELLED"])
            ).order_by(SyncJob.started_at.desc()).limit(limit)
        )
        jobs = list(result.scalars().all())

        # Total count
        count_result = await db.execute(
            select(func.count()).select_from(SyncJob).where(
                SyncJob.status.in_(["COMPLETED", "ERROR", "CANCELLED"])
            )
        )
        total = count_result.scalar() or 0

        return jobs, total

    @staticmethod
    async def update_job_progress(
        db: AsyncSession,
        job_id: UUID,
        current_item: Optional[str] = None,
        processed_items: Optional[int] = None,
        success_count: Optional[int] = None,
        failed_count: Optional[int] = None,
        fake_count: Optional[int] = None,
    ) -> Optional[SyncJob]:
        """Update sync job progress."""
        result = await db.execute(
            select(SyncJob).where(SyncJob.job_id == job_id)
        )
        job = result.scalar_one_or_none()
        if not job:
            return None

        if current_item is not None:
            job.current_item = current_item
        if processed_items is not None:
            job.processed_items = processed_items
        if success_count is not None:
            job.success_count = success_count
        if failed_count is not None:
            job.failed_count = failed_count
        if fake_count is not None:
            job.fake_count = fake_count

        await db.flush()
        return job

    @staticmethod
    async def complete_job(
        db: AsyncSession,
        job_id: UUID,
        status: str = "COMPLETED",
        error_message: Optional[str] = None,
    ) -> Optional[SyncJob]:
        """Mark sync job as complete."""
        result = await db.execute(
            select(SyncJob).where(SyncJob.job_id == job_id)
        )
        job = result.scalar_one_or_none()
        if not job:
            return None

        job.status = status
        job.completed_at = datetime.utcnow()
        job.current_item = None
        if error_message:
            job.error_message = error_message

        SyncService._active_job_id = None

        await db.flush()
        await db.refresh(job)
        logger.info(f"Completed sync job {job_id} with status {status}")
        return job

    @staticmethod
    async def process_queue_item(
        db: AsyncSession,
        job_id: UUID,
        part_number: str,
    ) -> dict:
        """
        Process a single queue item during sync.
        This is where the actual scraping would happen.
        
        Returns dict with result: SUCCESS, FAILED, or FAKE
        """
        # TODO: Implement actual scraping logic
        # For now, this is a placeholder that simulates scraping
        
        logger.info(f"Processing queue item: {part_number}")
        
        # Update job with current item
        await SyncService.update_job_progress(db, job_id, current_item=part_number)
        
        # Simulate scraping delay
        await asyncio.sleep(0.1)
        
        # In a real implementation:
        # 1. Try scraping from Mouser, DigiKey, AllDatasheet, etc.
        # 2. If found, create ICSpecification and remove from queue
        # 3. If not found after max retries, add to fake registry
        
        return {"part_number": part_number, "result": "PENDING"}

