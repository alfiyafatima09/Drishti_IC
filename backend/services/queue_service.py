"""Service for datasheet queue operations."""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from typing import Optional
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
    async def list_queue(db: AsyncSession) -> tuple[list[DatasheetQueue], int, int]:
        """List all queue items with counts."""
        # Get all items
        result = await db.execute(
            select(DatasheetQueue).order_by(DatasheetQueue.scan_count.desc())
        )
        items = result.scalars().all()
        
        # Count by status
        pending_count = sum(1 for item in items if item.status == "PENDING")
        failed_count = sum(1 for item in items if item.status == "FAILED")
        
        return list(items), pending_count, failed_count

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
    async def get_failed_items(db: AsyncSession) -> list[DatasheetQueue]:
        """Get failed items for retry."""
        result = await db.execute(
            select(DatasheetQueue).where(
                DatasheetQueue.status == "FAILED"
            ).order_by(DatasheetQueue.retry_count)  # Prioritize fewer retries
        )
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

