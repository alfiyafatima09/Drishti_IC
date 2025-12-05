"""Service for sync job operations."""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional, List
from datetime import datetime, timedelta
from uuid import UUID
import logging
import asyncio

from models import SyncJob, DatasheetQueue
from services.queue_service import QueueService
from services.fake_service import FakeService
from services.ic_service import ICService
from services.datasheet import datasheet_service
from core.constants import get_supported_manufacturers

logger = logging.getLogger(__name__)

# Max retries before marking as fake
MAX_RETRY_COUNT = 3


class SyncService:
    """Service for managing weekly sync operations."""

    # Track active job (simple in-memory tracking)
    _active_job_id: Optional[UUID] = None
    _cancel_requested: bool = False

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
        """Start a new sync job (creates job record, actual processing is separate)."""
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
        SyncService._cancel_requested = False
        logger.info(f"Started sync job {job.job_id} with {len(all_items)} items")

        return job

    @staticmethod
    async def run_sync_job(db: AsyncSession, job_id: UUID):
        """
        Run the actual sync processing in background.
        This is the main worker that processes queue items.
        """
        logger.info(f"Starting background sync processing for job {job_id}")
        
        try:
            # Get the job
            result = await db.execute(
                select(SyncJob).where(SyncJob.job_id == job_id)
            )
            job = result.scalar_one_or_none()
            if not job:
                logger.error(f"Sync job {job_id} not found")
                return
            
            # Get all items to process
            pending_items = await QueueService.get_pending_items(db)
            failed_items = await QueueService.get_failed_items(db)
            all_items = pending_items + [f for f in failed_items if f not in pending_items]
            
            if job.total_items > 0 and len(all_items) > job.total_items:
                all_items = all_items[:job.total_items]
            
            logger.info(f"Processing {len(all_items)} queue items")
            
            processed = 0
            success = 0
            failed = 0
            fake = 0
            
            for queue_item in all_items:
                # Check for cancellation
                if SyncService._cancel_requested:
                    logger.info(f"Sync job {job_id} cancelled by user")
                    break
                
                part_number = queue_item.part_number
                logger.info(f"Processing: {part_number} ({processed + 1}/{len(all_items)})")
                
                # Update current item
                job.current_item = part_number
                await db.commit()
                
                # Mark queue item as processing
                queue_item.status = "PROCESSING"
                await db.commit()
                
                try:
                    # Try to download datasheet from all manufacturers
                    result = await datasheet_service.download_datasheet(
                        part_number=part_number,
                        manufacturer_code=None,  # Try all manufacturers
                        db=db
                    )
                    
                    if result["success"]:
                        # SUCCESS - Found on at least one manufacturer
                        logger.info(f"SUCCESS: {part_number} found on {result['manufacturers_found']}")
                        
                        # Remove from queue (it's now in ic_specifications)
                        await QueueService.remove_from_queue(db, part_number)
                        success += 1
                        
                        # Add log entry
                        job.log = job.log + [{
                            "part_number": part_number,
                            "result": "SUCCESS",
                            "manufacturers": result["manufacturers_found"],
                            "timestamp": datetime.utcnow().isoformat()
                        }]
                    else:
                        # NOT FOUND on any manufacturer
                        queue_item.retry_count += 1
                        queue_item.error_message = result.get("message", "Not found on any manufacturer")
                        
                        if queue_item.retry_count >= MAX_RETRY_COUNT:
                            # Max retries reached - move to fake registry
                            logger.warning(f"FAKE: {part_number} not found after {MAX_RETRY_COUNT} attempts")
                            
                            try:
                                await FakeService.mark_as_fake(
                                    db=db,
                                    part_number=part_number,
                                    reason=f"Not found on any manufacturer website after {MAX_RETRY_COUNT} sync attempts",
                                    source="SYNC_NOT_FOUND",
                                    scrape_attempts=queue_item.retry_count,
                                    manufacturers_checked=get_supported_manufacturers(),
                                )
                            except ValueError:
                                # Already in fake registry
                                pass
                            
                            # Remove from queue
                            await QueueService.remove_from_queue(db, part_number)
                            fake += 1
                            
                            job.log = job.log + [{
                                "part_number": part_number,
                                "result": "FAKE",
                                "reason": "Not found after max retries",
                                "timestamp": datetime.utcnow().isoformat()
                            }]
                        else:
                            # Still has retries left - mark as failed for next sync
                            logger.info(f"FAILED: {part_number} (retry {queue_item.retry_count}/{MAX_RETRY_COUNT})")
                            queue_item.status = "FAILED"
                            failed += 1
                            
                            job.log = job.log + [{
                                "part_number": part_number,
                                "result": "FAILED",
                                "retry_count": queue_item.retry_count,
                                "timestamp": datetime.utcnow().isoformat()
                            }]
                    
                except Exception as e:
                    logger.error(f"Error processing {part_number}: {e}")
                    queue_item.status = "FAILED"
                    queue_item.error_message = str(e)
                    queue_item.retry_count += 1
                    failed += 1
                    
                    job.log = job.log + [{
                        "part_number": part_number,
                        "result": "ERROR",
                        "error": str(e),
                        "timestamp": datetime.utcnow().isoformat()
                    }]
                
                # Update job progress
                processed += 1
                job.processed_items = processed
                job.success_count = success
                job.failed_count = failed
                job.fake_count = fake
                
                # Commit after each item (so progress is saved)
                await db.commit()
            
            # Job complete
            if SyncService._cancel_requested:
                job.status = "CANCELLED"
                job.error_message = f"Cancelled by user. Processed {processed}/{len(all_items)} items."
            else:
                job.status = "COMPLETED"
            
            job.current_item = None
            job.completed_at = datetime.utcnow()
            
            SyncService._active_job_id = None
            SyncService._cancel_requested = False
            
            await db.commit()
            
            logger.info(
                f"Sync job {job_id} completed: "
                f"{success} success, {failed} failed, {fake} fake"
            )
            
        except Exception as e:
            logger.exception(f"Sync job {job_id} failed with error: {e}")
            
            # Try to mark job as error
            try:
                result = await db.execute(
                    select(SyncJob).where(SyncJob.job_id == job_id)
                )
                job = result.scalar_one_or_none()
                if job:
                    job.status = "ERROR"
                    job.error_message = str(e)
                    job.completed_at = datetime.utcnow()
                    job.current_item = None
                    await db.commit()
            except Exception:
                pass
            
            SyncService._active_job_id = None
            SyncService._cancel_requested = False

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

        # Signal cancellation to the background worker
        SyncService._cancel_requested = True
        
        # The actual status update will happen in run_sync_job
        # But we return current state for immediate feedback
        logger.info(f"Cancellation requested for sync job {active.job_id}")
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
