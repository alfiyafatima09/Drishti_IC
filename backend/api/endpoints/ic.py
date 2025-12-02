"""IC Database endpoints - Golden Record operations."""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from pathlib import Path
import logging

from backend.core.database import get_db
from backend.core.config import settings
from backend.services import ICService
from backend.schemas import ICSpecificationResponse, ICSearchResult

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/ic", tags=["IC Database"])


@router.get("/{part_number}/details", response_model=ICSpecificationResponse)
async def get_ic_details(
    part_number: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get IC specification from Golden Record.
    """
    ic = await ICService.get_by_part_number(db, part_number)
    
    if not ic:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "IC_NOT_FOUND",
                "message": f"Part number '{part_number}' not found in database.",
                "suggestion": "This IC may be in the sync queue or fake registry.",
            }
        )
    
    return ICSpecificationResponse(
        part_number=ic.part_number,
        manufacturer=ic.manufacturer,
        pin_count=ic.pin_count,
        package_type=ic.package_type,
        description=ic.description,
        datasheet_url=ic.datasheet_url,
        datasheet_path=ic.datasheet_path,
        has_datasheet=bool(ic.datasheet_path),
        voltage_min=ic.voltage_min,
        voltage_max=ic.voltage_max,
        operating_temp_min=ic.operating_temp_min,
        operating_temp_max=ic.operating_temp_max,
        electrical_specs=ic.electrical_specs,
        source=ic.source,
        created_at=ic.created_at,
        updated_at=ic.updated_at,
    )


@router.get("/{part_number}/datasheet")
async def get_ic_datasheet(
    part_number: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Download IC datasheet PDF.
    
    Returns the locally stored PDF file.
    """
    ic = await ICService.get_by_part_number(db, part_number)
    
    if not ic:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "IC_NOT_FOUND",
                "message": f"Part number '{part_number}' not found in database.",
            }
        )
    
    if not ic.datasheet_path:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "DATASHEET_NOT_FOUND",
                "message": f"Datasheet for '{part_number}' not available locally.",
            }
        )
    
    # Build full path
    datasheet_path = Path(ic.datasheet_path)
    if not datasheet_path.is_absolute():
        datasheet_path = settings.DATASHEET_FOLDER / datasheet_path.name
    
    if not datasheet_path.exists():
        raise HTTPException(
            status_code=404,
            detail={
                "error": "DATASHEET_NOT_FOUND",
                "message": f"Datasheet file not found at '{datasheet_path}'.",
            }
        )
    
    return FileResponse(
        path=datasheet_path,
        media_type="application/pdf",
        filename=f"{part_number}.pdf",
    )


@router.get("/search", response_model=ICSearchResult)
async def search_ics(
    q: str = Query(..., min_length=1, description="Search query"),
    manufacturer: Optional[str] = Query(None, description="Filter by manufacturer"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """
    Search IC database.
    """
    ics, total_count = await ICService.search(
        db=db,
        query=q,
        manufacturer=manufacturer,
        limit=limit,
        offset=offset,
    )
    
    return ICSearchResult(
        results=[
            {
                "part_number": ic.part_number,
                "manufacturer": ic.manufacturer,
                "pin_count": ic.pin_count,
                "package_type": ic.package_type,
                "description": ic.description,
            }
            for ic in ics
        ],
        total_count=total_count,
        limit=limit,
        offset=offset,
    )

