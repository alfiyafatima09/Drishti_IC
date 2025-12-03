"""
Database storage operations for datasheet metadata.
Handles storing and retrieving datasheet paths and metadata.
"""
import json
import logging
from typing import Optional, List, Dict
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy import text

from core.constants import Manufacturer, ICSource

logger = logging.getLogger(__name__)


async def get_datasheet_path_from_db(
    db: AsyncSession,
    part_number: str,
    manufacturer_code: str
) -> Optional[str]:
    """
    Get datasheet_path from database if it exists.
    
    Args:
        db: Database session
        part_number: IC part number
        manufacturer_code: Manufacturer enum code
        
    Returns:
        datasheet_path from database, or None if not found
    """
    try:
        query = text("""
            SELECT datasheet_path FROM ic_specifications 
            WHERE part_number = :part_number AND manufacturer = :manufacturer
            AND datasheet_path IS NOT NULL
            LIMIT 1
        """)
        result = await db.execute(
            query,
            {"part_number": part_number, "manufacturer": manufacturer_code}
        )
        row = result.fetchone()
        return row[0] if row else None
    except Exception as e:
        logger.debug(f"Could not read datasheet_path from database: {e}")
        return None


async def store_ic_specification(
    db: AsyncSession,
    part_number: str,
    manufacturer_code: str,
    datasheet_url: str,
    datasheet_path: str,
    source: ICSource,
    pin_count: int = 0,
    package_type: Optional[str] = None,
    description: Optional[str] = None,
    voltage_min: Optional[float] = None,
    voltage_max: Optional[float] = None,
    operating_temp_min: Optional[float] = None,
    operating_temp_max: Optional[float] = None,
    dimension_length: Optional[float] = None,
    dimension_width: Optional[float] = None,
    dimension_height: Optional[float] = None,
    electrical_specs: Optional[Dict] = None
) -> bool:
    """
    Store a single IC specification in database.
    Creates new record or updates existing one.
    
    Args:
        db: Database session
        part_number: IC part number (e.g., "LM317DCY")
        manufacturer_code: Manufacturer enum code
        datasheet_url: URL where datasheet was downloaded from
        datasheet_path: Local path where datasheet is stored
        source: Source enum (SCRAPED_STM, SCRAPED_TI, etc.)
        pin_count: Number of pins
        package_type: Package type (e.g., "SOT-223", "TO-220")
        description: IC description
        voltage_min: Minimum voltage
        voltage_max: Maximum voltage
        operating_temp_min: Minimum operating temperature
        operating_temp_max: Maximum operating temperature
        electrical_specs: Additional electrical specifications
        
    Returns:
        True if stored successfully, False otherwise
    """
    try:
        # Check if IC specification already exists
        check_query = text("""
            SELECT id FROM ic_specifications 
            WHERE part_number = :part_number AND manufacturer = :manufacturer
        """)
        check_result = await db.execute(
            check_query,
            {"part_number": part_number, "manufacturer": manufacturer_code}
        )
        existing = check_result.fetchone()
        
        if not existing:
            # Insert new record
            return await _insert_new_record(
                db, part_number, manufacturer_code, datasheet_url, datasheet_path,
                source, pin_count, package_type, description,
                voltage_min, voltage_max, operating_temp_min, operating_temp_max,
                dimension_length, dimension_width, dimension_height, electrical_specs
            )
        else:
            # Update existing record
            return await _update_existing_record(
                db, part_number, manufacturer_code, datasheet_url, datasheet_path,
                source, pin_count, package_type, description,
                voltage_min, voltage_max, operating_temp_min, operating_temp_max,
                dimension_length, dimension_width, dimension_height, electrical_specs
            )
            
    except IntegrityError:
        await db.rollback()
        logger.debug(
            f"IC specification for {part_number}/{manufacturer_code} already exists (unique constraint), skipping"
        )
        return False
    except Exception as e:
        await db.rollback()
        error_msg = str(e).lower()
        if "unique" in error_msg or "duplicate" in error_msg or "already exists" in error_msg:
            logger.debug(
                f"IC specification for {part_number}/{manufacturer_code} already exists, skipping"
            )
        else:
            logger.warning(f"Could not store IC specification in database: {e}")
        return False


async def store_multiple_ic_specifications(
    db: AsyncSession,
    ic_specs: List[Dict],
    manufacturer_code: str,
    datasheet_url: str,
    datasheet_path: str,
    source: ICSource
) -> int:
    """
    Store multiple IC specifications from a single PDF.
    Each IC variant gets its own database entry.
    Optimized to batch commits.
    
    Args:
        db: Database session
        ic_specs: List of IC specification dictionaries
        manufacturer_code: Manufacturer enum code
        datasheet_url: URL where datasheet was downloaded from
        datasheet_path: Local path where datasheet is stored
        source: Source enum
        
    Returns:
        Number of IC specifications successfully stored
    """
    stored_count = 0
    batch_size = 10  # Commit every 10 inserts for better performance
    
    for idx, ic_spec in enumerate(ic_specs, 1):
        success = await store_ic_specification(
            db=db,
            part_number=ic_spec.get("part_number", ""),
            manufacturer_code=manufacturer_code,
            datasheet_url=datasheet_url,
            datasheet_path=datasheet_path,
            source=source,
            pin_count=ic_spec.get("pin_count", 0),
            package_type=ic_spec.get("package_type"),
            description=ic_spec.get("description"),
            voltage_min=ic_spec.get("voltage_min"),
            voltage_max=ic_spec.get("voltage_max"),
            operating_temp_min=ic_spec.get("operating_temp_min"),
            operating_temp_max=ic_spec.get("operating_temp_max"),
            dimension_length=ic_spec.get("dimension_length"),
            dimension_width=ic_spec.get("dimension_width"),
            dimension_height=ic_spec.get("dimension_height"),
            electrical_specs=ic_spec.get("electrical_specs", {})
        )
        if success:
            stored_count += 1
    
    return stored_count


async def _insert_new_record(
    db: AsyncSession,
    part_number: str,
    manufacturer_code: str,
    datasheet_url: str,
    datasheet_path: str,
    source: ICSource,
    pin_count: int,
    package_type: Optional[str],
    description: Optional[str],
    voltage_min: Optional[float],
    voltage_max: Optional[float],
    operating_temp_min: Optional[float],
    operating_temp_max: Optional[float],
    dimension_length: Optional[float],
    dimension_width: Optional[float],
    dimension_height: Optional[float],
    electrical_specs: Optional[Dict]
) -> bool:
    """Insert new IC specification record."""
    inserted = False
    try:
        # Try with has_datasheet first
        insert_query = text("""
            INSERT INTO ic_specifications 
            (part_number, manufacturer, pin_count, package_type, description,
             datasheet_url, datasheet_path, has_datasheet, source,
             voltage_min, voltage_max, operating_temp_min, operating_temp_max,
             dimension_length, dimension_width, dimension_height, electrical_specs)
            VALUES (:part_number, :manufacturer, :pin_count, :package_type, :description,
                    :datasheet_url, :datasheet_path, :has_datasheet, :source,
                    :voltage_min, :voltage_max, :operating_temp_min, :operating_temp_max,
                    :dimension_length, :dimension_width, :dimension_height, :electrical_specs)
        """)
        # Convert dict to JSON string for PostgreSQL JSONB column
        electrical_specs_json = json.dumps(electrical_specs or {})
        
        await db.execute(
            insert_query,
            {
                "part_number": part_number,
                "manufacturer": manufacturer_code,
                "pin_count": pin_count,
                "package_type": package_type,
                "description": description,
                "datasheet_url": datasheet_url,
                "datasheet_path": datasheet_path,
                "has_datasheet": True,
                "source": source.value,
                "voltage_min": voltage_min,
                "voltage_max": voltage_max,
                "operating_temp_min": operating_temp_min,
                "operating_temp_max": operating_temp_max,
                "dimension_length": dimension_length,
                "dimension_width": dimension_width,
                "dimension_height": dimension_height,
                "electrical_specs": electrical_specs_json,
            }
        )
        inserted = True
    except Exception as e:
        error_msg = str(e).lower()
        await db.rollback()
        
        if "has_datasheet" in error_msg or "undefinedcolumn" in error_msg or "column" in error_msg:
            # Fallback: insert without has_datasheet
            try:
                insert_query = text("""
                    INSERT INTO ic_specifications 
                    (part_number, manufacturer, pin_count, package_type, description,
                     datasheet_url, datasheet_path, source,
                     voltage_min, voltage_max, operating_temp_min, operating_temp_max,
                     dimension_length, dimension_width, dimension_height, electrical_specs)
                    VALUES (:part_number, :manufacturer, :pin_count, :package_type, :description,
                            :datasheet_url, :datasheet_path, :source,
                            :voltage_min, :voltage_max, :operating_temp_min, :operating_temp_max,
                            :dimension_length, :dimension_width, :dimension_height, :electrical_specs)
                """)
                # Convert dict to JSON string for PostgreSQL JSONB column
                electrical_specs_json = json.dumps(electrical_specs or {})
                
                await db.execute(
                    insert_query,
                    {
                        "part_number": part_number,
                        "manufacturer": manufacturer_code,
                        "pin_count": pin_count,
                        "package_type": package_type,
                        "description": description,
                        "datasheet_url": datasheet_url,
                        "datasheet_path": datasheet_path,
                        "source": source.value,
                        "voltage_min": voltage_min,
                        "voltage_max": voltage_max,
                        "operating_temp_min": operating_temp_min,
                        "operating_temp_max": operating_temp_max,
                        "dimension_length": dimension_length,
                        "dimension_width": dimension_width,
                        "dimension_height": dimension_height,
                        "electrical_specs": electrical_specs_json,
                    }
                )
                inserted = True
            except Exception as e2:
                await db.rollback()
                raise e2
        else:
            raise
    
    if inserted:
        await db.commit()
    
    return inserted


async def _update_existing_record(
    db: AsyncSession,
    part_number: str,
    manufacturer_code: str,
    datasheet_url: str,
    datasheet_path: str,
    source: ICSource,
    pin_count: int,
    package_type: Optional[str],
    description: Optional[str],
    voltage_min: Optional[float],
    voltage_max: Optional[float],
    operating_temp_min: Optional[float],
    operating_temp_max: Optional[float],
    dimension_length: Optional[float],
    dimension_width: Optional[float],
    dimension_height: Optional[float],
    electrical_specs: Optional[Dict]
) -> bool:
    """Update existing IC specification record."""
    updated = False
    try:
        # Convert dict to JSON string for PostgreSQL JSONB column
        electrical_specs_json = json.dumps(electrical_specs or {}) if electrical_specs else None
        
        # Try with has_datasheet first
        update_query = text("""
            UPDATE ic_specifications 
            SET datasheet_url = :datasheet_url, 
                datasheet_path = :datasheet_path, 
                has_datasheet = :has_datasheet,
                pin_count = COALESCE(:pin_count, pin_count),
                package_type = COALESCE(:package_type, package_type),
                description = COALESCE(:description, description),
                voltage_min = COALESCE(:voltage_min, voltage_min),
                voltage_max = COALESCE(:voltage_max, voltage_max),
                operating_temp_min = COALESCE(:operating_temp_min, operating_temp_min),
                operating_temp_max = COALESCE(:operating_temp_max, operating_temp_max),
                dimension_length = COALESCE(:dimension_length, dimension_length),
                dimension_width = COALESCE(:dimension_width, dimension_width),
                dimension_height = COALESCE(:dimension_height, dimension_height),
                electrical_specs = COALESCE(CAST(:electrical_specs AS jsonb), electrical_specs),
                source = CASE WHEN source = 'MANUAL' THEN :source ELSE source END
            WHERE part_number = :part_number AND manufacturer = :manufacturer
        """)
        
        await db.execute(
            update_query,
            {
                "part_number": part_number,
                "manufacturer": manufacturer_code,
                "datasheet_url": datasheet_url,
                "datasheet_path": datasheet_path,
                "has_datasheet": True,
                "pin_count": pin_count,
                "package_type": package_type,
                "description": description,
                "voltage_min": voltage_min,
                "voltage_max": voltage_max,
                "operating_temp_min": operating_temp_min,
                "operating_temp_max": operating_temp_max,
                "dimension_length": dimension_length,
                "dimension_width": dimension_width,
                "dimension_height": dimension_height,
                "electrical_specs": electrical_specs_json,
                "source": source.value,
            }
        )
        updated = True
    except Exception as e:
        error_msg = str(e).lower()
        await db.rollback()
        
        if "has_datasheet" in error_msg or "undefinedcolumn" in error_msg or "column" in error_msg:
            # Fallback: update without has_datasheet
            try:
                # Convert dict to JSON string for PostgreSQL JSONB column
                electrical_specs_json = json.dumps(electrical_specs or {}) if electrical_specs else None
                
                update_query = text("""
                    UPDATE ic_specifications 
                    SET datasheet_url = :datasheet_url, 
                        datasheet_path = :datasheet_path,
                        pin_count = COALESCE(:pin_count, pin_count),
                        package_type = COALESCE(:package_type, package_type),
                        description = COALESCE(:description, description),
                        voltage_min = COALESCE(:voltage_min, voltage_min),
                        voltage_max = COALESCE(:voltage_max, voltage_max),
                        operating_temp_min = COALESCE(:operating_temp_min, operating_temp_min),
                        operating_temp_max = COALESCE(:operating_temp_max, operating_temp_max),
                        dimension_length = COALESCE(:dimension_length, dimension_length),
                        dimension_width = COALESCE(:dimension_width, dimension_width),
                        dimension_height = COALESCE(:dimension_height, dimension_height),
                        electrical_specs = COALESCE(CAST(:electrical_specs AS jsonb), electrical_specs),
                        source = CASE WHEN source = 'MANUAL' THEN :source ELSE source END
                    WHERE part_number = :part_number AND manufacturer = :manufacturer
                """)
                
                await db.execute(
                    update_query,
                    {
                        "part_number": part_number,
                        "manufacturer": manufacturer_code,
                        "datasheet_url": datasheet_url,
                        "datasheet_path": datasheet_path,
                        "pin_count": pin_count,
                        "package_type": package_type,
                        "description": description,
                        "voltage_min": voltage_min,
                        "voltage_max": voltage_max,
                        "operating_temp_min": operating_temp_min,
                        "operating_temp_max": operating_temp_max,
                        "dimension_length": dimension_length,
                        "dimension_width": dimension_width,
                        "dimension_height": dimension_height,
                        "electrical_specs": electrical_specs_json,
                        "source": source.value,
                    }
                )
                updated = True
            except Exception as e2:
                await db.rollback()
                raise e2
        else:
            raise
    
    if updated:
        await db.commit()
    
    return updated

