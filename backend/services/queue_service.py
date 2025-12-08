"""Service for datasheet queue operations."""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from typing import Optional, List
from datetime import datetime
import logging

from models import DatasheetQueue

logger = logging.getLogger(__name__)


class QueueService:
    """Service for managing the datasheet scraping queue."""

    @staticmethod
    async def add_to_queue(db: AsyncSession, part_number: str) -> DatasheetQueue:
        """Add a part number to the queue or increment scan count if exists."""
        normalized = part_number.strip().upper()
        
        # Check if already in queue
        existing = await QueueService.get_by_part_number(db, normalized)
        
        if existing:
            # Increment scan count and update last_scanned_at
            existing.scan_count += 1
            existing.last_scanned_at = datetime.utcnow()
            await db.flush()
            await db.refresh(existing)
            return existing
        
        # Create new entry
        queue_item = DatasheetQueue(
            part_number=normalized,
            first_seen_at=datetime.utcnow(),
            last_scanned_at=datetime.utcnow(),
            scan_count=1,
            status="PENDING",
        )
        db.add(queue_item)
        await db.flush()
        await db.refresh(queue_item)
        logger.info(f"Added '{normalized}' to datasheet queue")
        return queue_item

    @staticmethod
    async def get_by_part_number(
        db: AsyncSession, part_number: str
    ) -> Optional[DatasheetQueue]:
        """Get queue item by part number."""
        normalized = part_number.strip().upper()
        result = await db.execute(
            select(DatasheetQueue).where(
                func.upper(DatasheetQueue.part_number) == normalized
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_queue(
        db: AsyncSession,
        status_filter: Optional[List[str]] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[DatasheetQueue], int, int, int]:
        """
        List queue items with optional status filtering and pagination.
        
        Args:
            db: Database session
            status_filter: Optional list of statuses to filter by (e.g., ["PENDING", "FAILED"])
            limit: Maximum items to return
            offset: Number of items to skip
            
        Returns:
            Tuple of (items, total_count, pending_count, failed_count)
        """
        # Build base query
        query = select(DatasheetQueue)
        count_query = select(func.count()).select_from(DatasheetQueue)
        
        # Apply status filter if provided
        if status_filter:
            # Normalize status values to uppercase
            normalized_statuses = [s.upper() for s in status_filter]
            query = query.where(DatasheetQueue.status.in_(normalized_statuses))
            count_query = count_query.where(DatasheetQueue.status.in_(normalized_statuses))
        
        # Get total count for filtered results
        total_result = await db.execute(count_query)
        total_count = total_result.scalar() or 0
        
        # Apply ordering and pagination
        query = query.order_by(DatasheetQueue.scan_count.desc())
        query = query.limit(limit).offset(offset)
        
        result = await db.execute(query)
        items = list(result.scalars().all())
        
        # Get counts by status (for the full queue, not filtered)
        pending_result = await db.execute(
            select(func.count()).select_from(DatasheetQueue).where(
                DatasheetQueue.status == "PENDING"
            )
        )
        pending_count = pending_result.scalar() or 0
        
        failed_result = await db.execute(
            select(func.count()).select_from(DatasheetQueue).where(
                DatasheetQueue.status == "FAILED"
            )
        )
        failed_count = failed_result.scalar() or 0
        
        return items, total_count, pending_count, failed_count

    @staticmethod
    async def remove_from_queue(db: AsyncSession, part_number: str) -> bool:
        """Remove a part number from the queue."""
        normalized = part_number.strip().upper()
        
        result = await db.execute(
            delete(DatasheetQueue).where(
                func.upper(DatasheetQueue.part_number) == normalized
            )
        )
        
        deleted = result.rowcount > 0
        if deleted:
            logger.info(f"Removed '{normalized}' from datasheet queue")
        return deleted

    @staticmethod
    async def get_pending_items(
        db: AsyncSession, limit: Optional[int] = None
    ) -> list[DatasheetQueue]:
        """Get pending items for sync processing."""
        query = select(DatasheetQueue).where(
            DatasheetQueue.status == "PENDING"
        ).order_by(DatasheetQueue.scan_count.desc())  # Prioritize frequently seen
        
        if limit:
            query = query.limit(limit)
        
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_failed_items(
        db: AsyncSession, limit: Optional[int] = None
    ) -> list[DatasheetQueue]:
        """Get failed items for retry."""
        query = select(DatasheetQueue).where(
                DatasheetQueue.status == "FAILED"
            ).order_by(DatasheetQueue.retry_count)  # Prioritize fewer retries
        
        if limit:
            query = query.limit(limit)
        
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_items_by_status(
        db: AsyncSession,
        statuses: List[str],
        limit: Optional[int] = None
    ) -> list[DatasheetQueue]:
        """Get items matching any of the given statuses."""
        normalized_statuses = [s.upper() for s in statuses]
        
        query = select(DatasheetQueue).where(
            DatasheetQueue.status.in_(normalized_statuses)
        ).order_by(DatasheetQueue.scan_count.desc())
        
        if limit:
            query = query.limit(limit)
        
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def update_status(
        db: AsyncSession,
        part_number: str,
        status: str,
        error_message: Optional[str] = None,
    ) -> Optional[DatasheetQueue]:
        """Update queue item status."""
        item = await QueueService.get_by_part_number(db, part_number)
        if not item:
            return None
        
        item.status = status
        if error_message:
            item.error_message = error_message
        if status == "FAILED":
            item.retry_count += 1
        
        await db.flush()
        await db.refresh(item)
        return item

    @staticmethod
    async def get_queue_size(db: AsyncSession) -> int:
        """Get total queue size."""
        result = await db.execute(
            select(func.count()).select_from(DatasheetQueue)
        )
        return result.scalar() or 0
