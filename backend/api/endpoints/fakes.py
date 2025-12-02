"""Fake Registry endpoints - Counterfeit IC management."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from core.database import get_db
from services import FakeService
from schemas import (
    FakeListResult,
    FakeRegistryItem,
    MarkFakeRequest,
    SuccessResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/fakes", tags=["Fake Registry"])


@router.get("/list", response_model=FakeListResult)
async def list_fakes(
    db: AsyncSession = Depends(get_db),
):
    """
    List all known fake IC numbers.
    """
    items, total_count = await FakeService.list_fakes(db)
    
    return FakeListResult(
        fake_ics=[
            FakeRegistryItem(
                part_number=item.part_number,
                source=item.source,
                reason=item.reason,
                reported_by=item.reported_by,
                added_at=item.added_at,
                scrape_attempts=item.scrape_attempts,
                manufacturers_checked=item.manufacturers_checked,
            )
            for item in items
        ],
        total_count=total_count,
    )


@router.post("/mark", response_model=FakeRegistryItem)
async def mark_as_fake(
    request: MarkFakeRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Manually mark an IC as fake.
    """
    try:
        fake_entry = await FakeService.mark_as_fake(
            db=db,
            part_number=request.part_number,
            reason=request.reason,
            source="MANUAL_REPORT",
            reported_by=request.reported_by,
        )
        
        return FakeRegistryItem(
            part_number=fake_entry.part_number,
            source=fake_entry.source,
            reason=fake_entry.reason,
            reported_by=fake_entry.reported_by,
            added_at=fake_entry.added_at,
            scrape_attempts=fake_entry.scrape_attempts,
            manufacturers_checked=fake_entry.manufacturers_checked,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=409,
            detail={
                "error": "ALREADY_IN_REGISTRY",
                "message": str(e),
            }
        )


@router.delete("/{part_number}/unmark", response_model=SuccessResponse)
async def unmark_fake(
    part_number: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Remove an IC from the fake registry.
    
    Use this if an IC was marked as fake by mistake.
    """
    removed = await FakeService.unmark_fake(db, part_number)
    
    if not removed:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "NOT_IN_REGISTRY",
                "message": f"Part number '{part_number}' is not in the fake registry.",
            }
        )
    
    return SuccessResponse(
        success=True,
        message=f"Part number '{part_number}' removed from fake registry.",
    )

