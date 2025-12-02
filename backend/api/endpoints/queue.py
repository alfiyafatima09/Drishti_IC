"""Queue endpoints - Datasheet queue management."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from backend.core.database import get_db
from backend.services import QueueService
from backend.schemas import QueueListResult, QueueItem, SuccessResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/queue", tags=["Datasheet Queue"])


@router.get("/list", response_model=QueueListResult)
async def list_queue(
    db: AsyncSession = Depends(get_db),
):
    """
    List all pending ICs in the scraping queue.
    """
    items, pending_count, failed_count = await QueueService.list_queue(db)
    
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
        total_count=len(items),
        pending_count=pending_count,
        failed_count=failed_count,
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

