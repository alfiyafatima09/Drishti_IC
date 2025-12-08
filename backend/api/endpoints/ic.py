"""IC Database endpoints - Golden Record operations."""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import logging

from core.database import get_db
from services import ICService
from services.datasheet_storage import get_datasheet_path
from schemas import ICSpecificationResponse, ICSearchResult

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/ic", tags=["IC Database"])


@router.get("/details", response_model=ICSpecificationResponse)
async def get_ic_details(
    part_number: str = Query(..., description="IC part number (e.g., LM334SM/NOPB)"),
    db: AsyncSession = Depends(get_db),
):
    """Get IC specification from Golden Record."""
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


@router.get("/datasheet")
async def get_ic_datasheet(
    part_number: str = Query(..., description="IC part number (e.g., LM334SM/NOPB)"),
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

    logger.info(f"Looking up datasheet for {part_number}, DB path: {ic.datasheet_path}")

    # Use unified storage to resolve the path
    try:
        datasheet_path = get_datasheet_path(ic.datasheet_path)
        logger.info(f"Resolved datasheet path: {datasheet_path}")
    except ValueError as e:
        logger.error(f"Invalid datasheet path for {part_number}: {e}")
        raise HTTPException(
            status_code=404,
            detail={
                "error": "DATASHEET_NOT_FOUND",
                "message": f"Invalid datasheet path for '{part_number}'.",
            }
        )

    if not datasheet_path.exists():
        logger.warning(f"Datasheet file NOT FOUND at {datasheet_path} for {part_number} (DB value: {ic.datasheet_path})")
        raise HTTPException(
            status_code=404,
            detail={
                "error": "DATASHEET_NOT_FOUND",
                "message": f"Datasheet file not found for '{part_number}'. DB path: {ic.datasheet_path}, Resolved: {datasheet_path}",
            }
        )

    logger.info(f"Serving datasheet for {part_number} from {datasheet_path}")
    
    return FileResponse(
        path=datasheet_path,
        media_type="application/pdf",
        filename=f"{part_number}.pdf",
    )


@router.get("/search", response_model=ICSearchResult)
async def search_ics(
    q: str = Query(..., min_length=1, description="Search query"),
    manufacturer: Optional[str] = Query(None, description="Filter by manufacturer"),
    package_type: Optional[str] = Query(None, description="Filter by package type"),
    min_pins: Optional[int] = Query(2, ge=1, description="Minimum pin count (default 2 to filter invalid entries)"),
    max_pins: Optional[int] = Query(None, ge=1, description="Maximum pin count"),
    sort_by: str = Query("part_number", description="Sort field: part_number, manufacturer, pin_count, package_type, updated_at, created_at"),
    sort_dir: str = Query("asc", description="Sort direction: asc|desc"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Search IC database."""
    try:
        ics, total_count = await ICService.find(
            db=db,
            query=q,
            manufacturer=manufacturer,
            package_type=package_type,
            min_pins=min_pins,
            max_pins=max_pins,
            sort_by=sort_by,
            sort_dir=sort_dir,
            limit=limit,
            offset=offset,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    
    return ICSearchResult(
        results=[
            {
                "part_number": ic.part_number,
                "manufacturer": ic.manufacturer,
                "manufacturer_name": ic.manufacturer,
                "pin_count": ic.pin_count,
                "package_type": ic.package_type,
                "description": ic.description,
                "has_datasheet": bool(ic.datasheet_path),
            }
            for ic in ics
        ],
        total_count=total_count,
        limit=limit,
        offset=offset,
    )


@router.get("/list", response_model=ICSearchResult)
async def list_ics(
    manufacturer: Optional[str] = Query(None, description="Filter by manufacturer"),
    package_type: Optional[str] = Query(None, description="Filter by package type"),
    min_pins: Optional[int] = Query(2, ge=1, description="Minimum pin count (default 2 to filter invalid entries)"),
    max_pins: Optional[int] = Query(None, ge=1, description="Maximum pin count"),
    sort_by: str = Query("part_number", description="Sort field: part_number, manufacturer, pin_count, package_type, updated_at, created_at"),
    sort_dir: str = Query("asc", description="Sort direction: asc|desc"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List ICs with pagination, filters, and sorting (no text query required)."""
    try:
        ics, total_count = await ICService.find(
            db=db,
            query=None,
            manufacturer=manufacturer,
            package_type=package_type,
            min_pins=min_pins,
            max_pins=max_pins,
            sort_by=sort_by,
            sort_dir=sort_dir,
            limit=limit,
            offset=offset,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return ICSearchResult(
        results=[
            {
                "part_number": ic.part_number,
                "manufacturer": ic.manufacturer,
                "manufacturer_name": ic.manufacturer,
                "pin_count": ic.pin_count,
                "package_type": ic.package_type,
                "description": ic.description,
                "has_datasheet": bool(ic.datasheet_path),
            }
            for ic in ics
        ],
        total_count=total_count,
        limit=limit,
        offset=offset,
    )
