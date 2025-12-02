"""Service for fake registry operations."""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from typing import Optional
from datetime import datetime
import logging

from backend.models import FakeRegistry

logger = logging.getLogger(__name__)


class FakeService:
    """Service for managing the fake IC registry."""

    @staticmethod
    async def get_by_part_number(
        db: AsyncSession, part_number: str
    ) -> Optional[FakeRegistry]:
        """Check if a part number is in the fake registry."""
        normalized = part_number.strip().upper()
        result = await db.execute(
            select(FakeRegistry).where(
                func.upper(FakeRegistry.part_number) == normalized
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def is_fake(db: AsyncSession, part_number: str) -> bool:
        """Quick check if a part number is fake."""
        entry = await FakeService.get_by_part_number(db, part_number)
        return entry is not None

    @staticmethod
    async def list_fakes(db: AsyncSession) -> tuple[list[FakeRegistry], int]:
        """List all fake registry entries."""
        result = await db.execute(
            select(FakeRegistry).order_by(FakeRegistry.added_at.desc())
        )
        items = list(result.scalars().all())
        return items, len(items)

    @staticmethod
    async def mark_as_fake(
        db: AsyncSession,
        part_number: str,
        reason: str,
        source: str = "MANUAL_REPORT",
        reported_by: Optional[str] = None,
        scrape_attempts: int = 0,
        manufacturers_checked: Optional[list[str]] = None,
    ) -> FakeRegistry:
        """Add a part number to the fake registry."""
        normalized = part_number.strip().upper()
        
        # Check if already exists
        existing = await FakeService.get_by_part_number(db, normalized)
        if existing:
            raise ValueError(f"Part number '{normalized}' is already in fake registry")
        
        fake_entry = FakeRegistry(
            part_number=normalized,
            source=source,
            reason=reason,
            reported_by=reported_by,
            scrape_attempts=scrape_attempts,
            manufacturers_checked=manufacturers_checked,
            added_at=datetime.utcnow(),
        )
        
        db.add(fake_entry)
        await db.flush()
        await db.refresh(fake_entry)
        logger.info(f"Marked '{normalized}' as fake: {reason}")
        return fake_entry

    @staticmethod
    async def unmark_fake(db: AsyncSession, part_number: str) -> bool:
        """Remove a part number from the fake registry."""
        normalized = part_number.strip().upper()
        
        result = await db.execute(
            delete(FakeRegistry).where(
                func.upper(FakeRegistry.part_number) == normalized
            )
        )
        
        deleted = result.rowcount > 0
        if deleted:
            logger.info(f"Removed '{normalized}' from fake registry")
        return deleted

    @staticmethod
    async def get_count(db: AsyncSession) -> int:
        """Get total count of fake registry entries."""
        result = await db.execute(
            select(func.count()).select_from(FakeRegistry)
        )
        return result.scalar() or 0

