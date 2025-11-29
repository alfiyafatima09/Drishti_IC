"""
Datasheet management routes for IC specifications
"""
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import Optional
import os

from models.database import get_db, IC, DatasheetCache
from services.datasheet_service import DatasheetService
from config.settings import settings

router = APIRouter()
datasheet_service = DatasheetService()


@router.post("/datasheets/fetch/{part_number}")
async def fetch_datasheet(
    background_tasks: BackgroundTasks,
    part_number: str,
    manufacturer: Optional[str] = None,
    force_refresh: Optional[bool] = False,
    db: Session = Depends(get_db)
):
    """Fetch datasheet for a specific IC part number"""

    try:
        result = await datasheet_service.fetch_datasheet(
            part_number, manufacturer, force_refresh
        )

        ic = db.query(IC).filter_by(part_number=part_number).first()
        if ic:
            ic.datasheet_url = result.get("url")
            ic.datasheet_path = result.get("local_path")
            ic.datasheet_last_updated = result.get("downloaded_at")
            db.commit()

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Datasheet fetch failed: {str(e)}")


@router.get("/datasheets/{part_number}")
async def get_datasheet(part_number: str, db: Session = Depends(get_db)):
    """Get cached datasheet for an IC"""

    # Check database first
    ic = db.query(IC).filter_by(part_number=part_number).first()
    if ic and ic.datasheet_path and os.path.exists(ic.datasheet_path):
        return FileResponse(
            ic.datasheet_path,
            media_type="application/pdf",
            filename=f"{part_number}_datasheet.pdf"
        )

    # Check cache
    cache_entry = db.query(DatasheetCache).filter_by(
        url=datasheet_service.generate_datasheet_url(part_number)
    ).first()

    if cache_entry and os.path.exists(cache_entry.local_path):
        return FileResponse(
            cache_entry.local_path,
            media_type="application/pdf",
            filename=f"{part_number}_datasheet.pdf"
        )

    raise HTTPException(status_code=404, detail="Datasheet not found")


@router.post("/datasheets/parse/{part_number}")
async def parse_datasheet(
    part_number: str,
    datasheet_file: Optional[bytes] = None,
    db: Session = Depends(get_db)
):
    """Parse datasheet and extract IC specifications"""

    try:
       
        if datasheet_file:
            content = datasheet_file
        else:
           
            ic = db.query(IC).filter_by(part_number=part_number).first()
            if ic and ic.datasheet_path and os.path.exists(ic.datasheet_path):
                with open(ic.datasheet_path, "rb") as f:
                    content = f.read()
            else:
                raise HTTPException(status_code=404, detail="Datasheet not available")

        specs = await datasheet_service.parse_datasheet(content)

        ic = db.query(IC).filter_by(part_number=part_number).first()
        if ic:
            ic.operating_voltage_min = specs.get("operating_voltage_min")
            ic.operating_voltage_max = specs.get("operating_voltage_max")
            ic.current_rating = specs.get("current_rating")
            ic.temperature_min = specs.get("temperature_min")
            ic.temperature_max = specs.get("temperature_max")
            ic.pin_count = specs.get("pin_count")
            ic.package_type = specs.get("package_type")
            ic.marking_specifications = specs.get("marking_specs")
            ic.font_specifications = specs.get("font_specs")
            ic.logo_requirements = specs.get("logo_requirements")
            ic.other_specs = specs.get("other_specs", {})

            db.commit()

        return specs

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Datasheet parsing failed: {str(e)}")


@router.get("/datasheets/search")
async def search_ic_database(
    query: str,
    manufacturer: Optional[str] = None,
    limit: Optional[int] = 20,
    db: Session = Depends(get_db)
):
    """Search IC database for specifications"""

    try:
        results = await datasheet_service.search_ic_database(query, manufacturer, limit)
        return {"results": results}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database search failed: {str(e)}")


@router.post("/datasheets/ic/add")
async def add_ic_to_database(
    part_number: str,
    manufacturer_name: str,
    specifications: dict,
    db: Session = Depends(get_db)
):
    """Manually add IC specifications to database"""

    try:
        from models.database import Manufacturer
        manufacturer = db.query(Manufacturer).filter_by(name=manufacturer_name).first()
        if not manufacturer:
            manufacturer = Manufacturer(name=manufacturer_name)
            db.add(manufacturer)
            db.commit()
            db.refresh(manufacturer)

        existing_ic = db.query(IC).filter_by(part_number=part_number).first()
        if existing_ic:
            raise HTTPException(status_code=400, detail="IC already exists in database")

        ic = IC(
            part_number=part_number,
            manufacturer_id=manufacturer.id,
            operating_voltage_min=specifications.get("operating_voltage_min"),
            operating_voltage_max=specifications.get("operating_voltage_max"),
            operating_voltage_unit=specifications.get("operating_voltage_unit", "V"),
            current_rating=specifications.get("current_rating"),
            current_unit=specifications.get("current_unit", "A"),
            temperature_min=specifications.get("temperature_min"),
            temperature_max=specifications.get("temperature_max"),
            temperature_unit=specifications.get("temperature_unit", "°C"),
            pin_count=specifications.get("pin_count"),
            package_type=specifications.get("package_type"),
            dimensions=specifications.get("dimensions"),
            marking_specifications=specifications.get("marking_specifications"),
            font_specifications=specifications.get("font_specifications"),
            logo_requirements=specifications.get("logo_requirements"),
            other_specs=specifications.get("other_specs", {})
        )

        db.add(ic)
        db.commit()
        db.refresh(ic)

        return {"message": "IC added successfully", "ic_id": ic.id}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add IC: {str(e)}")


@router.get("/datasheets/cache/stats")
async def get_cache_stats(db: Session = Depends(get_db)):
    """Get datasheet cache statistics"""

    try:
        total_cached = db.query(DatasheetCache).count()
        total_size = db.query(DatasheetCache).with_entities(
            db.func.sum(DatasheetCache.file_size_bytes)
        ).scalar() or 0

        return {
            "total_cached_datasheets": total_cached,
            "total_cache_size_bytes": total_size,
            "total_cache_size_mb": round(total_size / (1024 * 1024), 2),
            "cache_directory": settings.datasheet_cache_dir
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cache stats retrieval failed: {str(e)}")


@router.delete("/datasheets/cache/clear")
async def clear_cache(db: Session = Depends(get_db)):
    """Clear datasheet cache"""

    try:
        deleted_count = db.query(DatasheetCache).delete()
        db.commit()

        return {"message": f"Cleared {deleted_count} cached datasheets"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cache clear failed: {str(e)}")
