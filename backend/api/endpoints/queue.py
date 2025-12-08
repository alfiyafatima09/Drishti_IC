"""Queue endpoints - Datasheet queue management."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
import logging

from core.database import get_db
from services import QueueService
from schemas import QueueListResult, QueueItem, SuccessResponse, QueueAddRequest, QueueAddResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/queue", tags=["Datasheet Queue"])


@router.get("/list", response_model=QueueListResult)
async def list_queue(
    status: Optional[List[str]] = Query(
        None, 
        description="Filter by status(es). Can specify multiple: ?status=PENDING&status=FAILED"
    ),
    limit: int = Query(100, ge=1, le=500, description="Maximum items to return"),
    offset: int = Query(0, ge=0, description="Number of items to skip"),
    db: AsyncSession = Depends(get_db),
):
    """
    List ICs in the scraping queue with optional status filtering and pagination.
    
    Status options: PENDING, PROCESSING, FAILED
    """
    items, total_count, pending_count, failed_count = await QueueService.list_queue(
        db, 
        status_filter=status,
        limit=limit,
        offset=offset,
    )
    
    return QueueListResult(
        queue_items=[
            QueueItem(
                part_number=item.part_number,
                first_seen_at=item.first_seen_at,
                last_scanned_at=item.last_scanned_at,
                scan_count=item.scan_count,
                status=item.status,
                retry_count=item.retry_count,
                error_message=item.error_message,
            )
            for item in items
        ],
        total_count=total_count,
        pending_count=pending_count,
        failed_count=failed_count,
        limit=limit,
        offset=offset,
    )


@router.post("/add", response_model=QueueAddResponse)
async def add_to_queue(
    request: QueueAddRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Manually add part number(s) to the sync queue.
    
    Use this to queue ICs for datasheet fetching. Duplicate entries
    will increment the scan_count instead of creating new entries.
    """
    queued_items = []
    already_queued = 0
    
    for part_number in request.part_numbers:
        # Check if already exists
        existing = await QueueService.get_by_part_number(db, part_number)
        if existing:
            already_queued += 1
        
        # Add or update (increments scan_count if exists)
        await QueueService.add_to_queue(db, part_number)
        queued_items.append(part_number.strip().upper())
    
    added_count = len(request.part_numbers) - already_queued
    
    logger.info(f"Queue add request: {len(request.part_numbers)} items, {added_count} new, {already_queued} updated")
    
    return QueueAddResponse(
        success=True,
        added_count=added_count,
        already_queued_count=already_queued,
        message=f"Added {added_count} new items to queue, updated {already_queued} existing items.",
        queued_items=queued_items,
    )


@router.delete("/{part_number}/remove", response_model=SuccessResponse)
async def remove_from_queue(
    part_number: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Remove a part number from the queue.
    
    Use this if an IC was added by mistake.
    """
    removed = await QueueService.remove_from_queue(db, part_number)
    
    if not removed:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "NOT_IN_QUEUE",
                "message": f"Part number '{part_number}' is not in the queue.",
            }
        )
    
    return SuccessResponse(
        success=True,
        message=f"Part number '{part_number}' removed from sync queue.",
    )
