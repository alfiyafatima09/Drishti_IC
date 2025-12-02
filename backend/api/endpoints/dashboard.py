"""Dashboard endpoints - Statistics and analytics."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from core.database import get_db
from services import DashboardService
from schemas import DashboardStats

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/dashboard", tags=["Dashboard"])


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
):
    """
    Get dashboard statistics.
    
    Returns comprehensive stats including:
    - Scan counts (total, today, this week)
    - Status breakdown (pass, fail, unknown, counterfeit)
    - Pass rate percentage
    - Queue and registry sizes
    - Last sync info
    - Recent counterfeits
    """
    stats = await DashboardService.get_stats(db)
    return stats

