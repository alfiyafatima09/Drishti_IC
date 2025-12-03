"""Service for dashboard statistics."""
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from datetime import datetime
import logging

from services.scan_service import ScanService
from services.ic_service import ICService
from services.queue_service import QueueService
from services.fake_service import FakeService
from services.sync_service import SyncService
from schemas import DashboardStats

logger = logging.getLogger(__name__)


class DashboardService:
    """Service for dashboard statistics aggregation."""

    @staticmethod
    async def get_stats(db: AsyncSession) -> DashboardStats:
        """Get comprehensive dashboard statistics."""
        # Get scan stats
        scan_stats = await ScanService.get_stats(db)
        
        # Get IC count
        ic_count = await ICService.get_count(db)
        
        # Get queue size
        queue_items, pending_count, failed_count = await QueueService.list_queue(db)
        queue_size = len(queue_items)
        
        # Get fake registry size
        fake_count = await FakeService.get_count(db)
        
        # Get last sync info
        sync_history, _ = await SyncService.get_history(db, limit=1)
        last_sync_at = None
        last_sync_status = None
        if sync_history:
            last_sync = sync_history[0]
            last_sync_at = last_sync.completed_at or last_sync.started_at
            last_sync_status = last_sync.status
        
        return DashboardStats(
            total_scans=scan_stats["total_scans"],
            scans_today=scan_stats["scans_today"],
            scans_this_week=scan_stats["scans_this_week"],
            pass_count=scan_stats["pass_count"],
            fail_count=scan_stats["fail_count"],
            unknown_count=scan_stats["unknown_count"],
            counterfeit_count=scan_stats["counterfeit_count"],
            pass_rate_percentage=scan_stats["pass_rate_percentage"],
            queue_size=queue_size,
            fake_registry_size=fake_count,
            database_ic_count=ic_count,
            last_sync_at=last_sync_at,
            last_sync_status=last_sync_status,
            recent_counterfeits=[
                {"part_number": c["part_number"], "scanned_at": datetime.fromisoformat(c["scanned_at"]) if c["scanned_at"] else None}
                for c in scan_stats["recent_counterfeits"]
            ],
        )

