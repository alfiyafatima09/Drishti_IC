"""
Digikey-related API endpoints.

Provides a POST endpoint to search Digikey by keyword, download the first
datasheet PDF found, parse it to extract IC specifications, and return the results.

Uses a hybrid approach:
1. Parse PDF datasheet for detailed IC specifications
2. Fill in any missing fields from DigiKey API response
3. Store extracted data in database
"""
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from pathlib import Path
from typing import List, Optional, Dict, Any
import logging
import re
import json

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from services.digikey import digi_service, DigiKeyException
from services.pdf_parser import parse_pdf
from core.config import settings
from core.database import get_db
from models.ic_specification import ICSpecification

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/digikey", tags=["digikey"])


class DigiKeySearchRequest(BaseModel):
    keyword: str = Field(..., description="Keyword to search on Digikey (e.g. 'lm358')")


class ICVariant(BaseModel):
    """IC variant specification extracted from datasheet."""
    part_number: str
    manufacturer: str
    pin_count: int
    package_type: Optional[str] = None
    description: str
    voltage_min: Optional[float] = None
    voltage_max: Optional[float] = None
    operating_temp_min: Optional[float] = None
    operating_temp_max: Optional[float] = None
    dimension_length: Optional[float] = None
    dimension_width: Optional[float] = None
    dimension_height: Optional[float] = None
    electrical_specs: Dict[str, Any] = {}


class DigiKeySearchResponse(BaseModel):
    """Response containing datasheet path and parsed IC specifications."""
    datasheet_path: str
    manufacturer: Optional[str] = None
    parse_status: str
    total_variants: int
    ic_variants: List[ICVariant]
    saved_to_db: int = 0  # Number of variants saved/updated in database
    error: Optional[str] = None


async def save_variants_to_db(
    db: AsyncSession,
    variants: List[Dict[str, Any]],
    datasheet_url: str,
    datasheet_path: str
) -> int:
    """
    Save or update IC variants in the database.
    Uses upsert (insert on conflict update) to handle duplicates.

    Args:
        db: Database session
        variants: List of IC variant dictionaries
        datasheet_url: Original datasheet URL
        datasheet_path: Local path to downloaded PDF

    Returns:
        Number of records saved/updated
    """
    saved_count = 0

    for variant in variants:
        try:
            # Normalize manufacturer code using centralized mapping
            from core.constants import get_manufacturer_code_from_name
            manufacturer = variant.get("manufacturer", "")
            normalized = get_manufacturer_code_from_name(manufacturer)
            if normalized:
                manufacturer = normalized
            else:
                manufacturer = manufacturer.upper()

            # Prepare the data for upsert
            ic_data = {
                "part_number": variant["part_number"],
                "manufacturer": manufacturer,
                "pin_count": variant.get("pin_count") or 0,
                "package_type": variant.get("package_type"),
                "description": variant.get("description"),
                "datasheet_url": datasheet_url,
                "datasheet_path": str(datasheet_path),
                "has_datasheet": True,
                "voltage_min": variant.get("voltage_min"),
                "voltage_max": variant.get("voltage_max"),
                "operating_temp_min": variant.get("operating_temp_min"),
                "operating_temp_max": variant.get("operating_temp_max"),
                "dimension_length": variant.get("dimension_length"),
                "dimension_width": variant.get("dimension_width"),
                "dimension_height": variant.get("dimension_height"),
                "electrical_specs": variant.get("electrical_specs") or {},
                "source": "DIGIKEY_API",
            }

            # PostgreSQL upsert: INSERT ... ON CONFLICT DO UPDATE
            stmt = insert(ICSpecification).values(**ic_data)
            stmt = stmt.on_conflict_do_update(
                constraint="uq_ic_part_manufacturer",
                set_={
                    "pin_count": stmt.excluded.pin_count,
                    "package_type": stmt.excluded.package_type,
                    "description": stmt.excluded.description,
                    "datasheet_url": stmt.excluded.datasheet_url,
                    "datasheet_path": stmt.excluded.datasheet_path,
                    "has_datasheet": stmt.excluded.has_datasheet,
                    "voltage_min": stmt.excluded.voltage_min,
                    "voltage_max": stmt.excluded.voltage_max,
                    "operating_temp_min": stmt.excluded.operating_temp_min,
                    "operating_temp_max": stmt.excluded.operating_temp_max,
                    "dimension_length": stmt.excluded.dimension_length,
                    "dimension_width": stmt.excluded.dimension_width,
                    "dimension_height": stmt.excluded.dimension_height,
                    "electrical_specs": stmt.excluded.electrical_specs,
                    "source": stmt.excluded.source,
                }
            )

            await db.execute(stmt)
            saved_count += 1
            logger.debug(f"Saved/updated IC: {variant['part_number']} ({manufacturer})")

        except Exception as e:
            logger.error(f"Failed to save IC {variant.get('part_number')}: {e}")
            continue

    # Note: No need to commit manually - the get_db() dependency handles transaction commit
    await db.flush()  # Flush to ensure changes are sent to DB, but don't commit yet
    logger.info(f"Saved {saved_count} IC variants to database")

    return saved_count


def parse_digikey_parameters(product: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse DigiKey API product parameters to extract useful specifications.

    Args:
        product: DigiKey product object from API response

    Returns:
        Dictionary with parsed specifications
    """
    specs = {
        "voltage_min": None,
        "voltage_max": None,
        "operating_temp_min": None,
        "operating_temp_max": None,
        "pin_count": None,
        "package_type": None,
        "description": None,
    }

    # Get description
    desc = product.get("Description", {})
    if isinstance(desc, dict):
        specs["description"] = desc.get("DetailedDescription") or desc.get("ProductDescription")

    # Parse parameters
    parameters = product.get("Parameters", [])
    for param in parameters:
        param_text = param.get("ParameterText", "").lower()
        value_text = param.get("ValueText", "")

        if not value_text:
            continue

        # Voltage - Supply (Vcc/Vdd): "2.95V ~ 5.5V" or "2.4V ~ 3.6V"
        if "voltage" in param_text and "supply" in param_text:
            voltage_match = re.search(r'(\d+\.?\d*)\s*V?\s*[~\-–to]+\s*(\d+\.?\d*)\s*V?', value_text)
            if voltage_match:
                try:
                    specs["voltage_min"] = float(voltage_match.group(1))
                    specs["voltage_max"] = float(voltage_match.group(2))
                except ValueError:
                    pass

        # Operating Temperature: "-40°C ~ 85°C (TA)"
        if "operating temperature" in param_text:
            temp_match = re.search(r'(-?\d+)\s*°?\s*C?\s*[~\-–to]+\s*\+?(\d+)', value_text)
            if temp_match:
                try:
                    specs["operating_temp_min"] = float(temp_match.group(1))
                    specs["operating_temp_max"] = float(temp_match.group(2))
                except ValueError:
                    pass

        # Number of I/O or Pin count
        if "number of i/o" in param_text or "pin" in param_text:
            pin_match = re.search(r'(\d+)', value_text)
            if pin_match:
                try:
                    specs["pin_count"] = int(pin_match.group(1))
                except ValueError:
                    pass

        # Package / Case: "20-TSSOP (0.173", 4.40mm Width)"
        if "package" in param_text or "case" in param_text:
            # Extract package type like "20-TSSOP" or "TSSOP20"
            pkg_match = re.search(r'(\d+)[\-]?([A-Z]{2,})', value_text)
            if pkg_match:
                specs["package_type"] = f"{pkg_match.group(2)}{pkg_match.group(1)}"
            else:
                pkg_match = re.search(r'([A-Z]{2,})[\-]?(\d+)', value_text)
                if pkg_match:
                    specs["package_type"] = f"{pkg_match.group(1)}{pkg_match.group(2)}"

        # Supplier Device Package: "20-TSSOP"
        if "supplier device package" in param_text:
            pkg_match = re.search(r'(\d+)[\-]?([A-Z]+)', value_text)
            if pkg_match and not specs["package_type"]:
                specs["package_type"] = f"{pkg_match.group(2)}{pkg_match.group(1)}"

    return specs


def merge_variant_with_api_data(variant: Dict[str, Any], api_specs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge PDF-extracted variant data with DigiKey API data.
    PDF data takes precedence; API data fills in missing fields.

    Args:
        variant: IC variant data extracted from PDF
        api_specs: Specifications parsed from DigiKey API

    Returns:
        Merged variant dictionary
    """
    merged = variant.copy()

    # Fill in missing voltage specs
    if merged.get("voltage_min") is None and api_specs.get("voltage_min") is not None:
        merged["voltage_min"] = api_specs["voltage_min"]
    if merged.get("voltage_max") is None and api_specs.get("voltage_max") is not None:
        merged["voltage_max"] = api_specs["voltage_max"]

    # Fill in missing temperature specs
    if merged.get("operating_temp_min") is None and api_specs.get("operating_temp_min") is not None:
        merged["operating_temp_min"] = api_specs["operating_temp_min"]
    if merged.get("operating_temp_max") is None and api_specs.get("operating_temp_max") is not None:
        merged["operating_temp_max"] = api_specs["operating_temp_max"]

    # Fill in missing pin count (if 0 or None)
    if (merged.get("pin_count") is None or merged.get("pin_count") == 0) and api_specs.get("pin_count"):
        merged["pin_count"] = api_specs["pin_count"]

    # Fill in missing package type
    if not merged.get("package_type") and api_specs.get("package_type"):
        merged["package_type"] = api_specs["package_type"]

    # Update description if empty
    if (not merged.get("description") or merged["description"].startswith("NXP ") and " - " not in merged["description"]):
        if api_specs.get("description"):
            merged["description"] = api_specs["description"]

    return merged


@router.post("/search")
async def digikey_search(
    request: DigiKeySearchRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Search DigiKey for IC by keyword, download datasheet, and extract specifications.

    Uses a hybrid approach:
    1. Search DigiKey API and extract specifications from response
    2. Download and parse PDF datasheet for detailed IC variants
    3. Merge data - PDF data takes precedence, API fills gaps
    4. Store extracted data in database

    Args:
        request: Contains the search keyword (e.g., "lm358")
        db: Database session (injected)

    Returns:
        Pretty-printed JSON with datasheet path and extracted IC specifications
        including part numbers, pin counts, voltage ranges, temperature ranges, etc.
    """
    keyword = request.keyword.strip()
    if not keyword:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="keyword is required")

    api_specs = {}
    local_pdf = None
    manufacturer = None
    datasheet_url = None

    try:
        # Step 1: Search DigiKey API
        search_response = digi_service.search_keyword(keyword)

        # Extract datasheet info
        datasheet_info = digi_service.extract_first_datasheet_info(search_response)
        if not datasheet_info:
            raise DigiKeyException("No datasheet URL found in search response")

        datasheet_url = datasheet_info["url"]

        # Parse API parameters for specs
        products = search_response.get("Products", [])
        if products:
            api_specs = parse_digikey_parameters(products[0])
            logger.info(f"Extracted API specs: voltage={api_specs.get('voltage_min')}-{api_specs.get('voltage_max')}V, "
                       f"temp={api_specs.get('operating_temp_min')}-{api_specs.get('operating_temp_max')}C, "
                       f"package={api_specs.get('package_type')}")

        # Step 2: Download PDF
        manufacturer = datasheet_info["manufacturer"]
        local_pdf = digi_service.download_pdf(
            datasheet_url,
            manufacturer=manufacturer
        )

    except DigiKeyException as e:
        logger.error("Digikey search/download error: %s", e)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))
    except Exception as e:
        logger.exception("Unexpected error in digikey_search")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    # Step 3: Parse PDF to extract IC specifications
    try:
        parsed = parse_pdf(Path(local_pdf), manufacturer=manufacturer)

        # Step 4: Merge PDF data with API data
        ic_variants = []
        variants_to_save = []  # Collect variants for DB save
        
        for variant_data in parsed.get("ic_variants", []):
            merged_variant = merge_variant_with_api_data(variant_data, api_specs)
            ic_variants.append(ICVariant(**merged_variant))
            variants_to_save.append(merged_variant)

        # If no variants from PDF but we have API specs, create one from API
        if not ic_variants and api_specs:
            logger.info("No variants from PDF, creating from API data")
            api_variant = {
                "part_number": keyword.upper(),
                "manufacturer": manufacturer or "Unknown",
                "pin_count": api_specs.get("pin_count") or 0,
                "package_type": api_specs.get("package_type"),
                "description": api_specs.get("description") or f"{manufacturer} {keyword}",
                "voltage_min": api_specs.get("voltage_min"),
                "voltage_max": api_specs.get("voltage_max"),
                "operating_temp_min": api_specs.get("operating_temp_min"),
                "operating_temp_max": api_specs.get("operating_temp_max"),
                "dimension_length": None,
                "dimension_width": None,
                "dimension_height": None,
                "electrical_specs": {}
            }
            ic_variants.append(ICVariant(**api_variant))
            variants_to_save.append(api_variant)

        # Step 5: Save variants to database
        saved_count = 0
        if variants_to_save:
            try:
                saved_count = await save_variants_to_db(
                    db=db,
                    variants=variants_to_save,
                    datasheet_url=datasheet_url,
                    datasheet_path=str(local_pdf)
                )
                logger.info(f"Saved {saved_count}/{len(variants_to_save)} variants to database")
            except Exception as db_error:
                logger.error(f"Database save failed: {db_error}")
                # Continue even if DB save fails

        response_data = DigiKeySearchResponse(
            datasheet_path=str(local_pdf),
            manufacturer=parsed.get("manufacturer") or manufacturer,
            parse_status=parsed.get("status", "unknown"),
            total_variants=len(ic_variants),
            ic_variants=ic_variants,
            saved_to_db=saved_count,
            error=parsed.get("error")
        )
        
        # Return pretty-printed JSON
        return JSONResponse(
            content=json.loads(response_data.model_dump_json()),
            media_type="application/json"
        )

    except Exception as e:
        logger.exception("PDF parsing failed for %s", local_pdf)

        # Return response with API data if PDF parsing fails
        if api_specs:
            api_variant = {
                "part_number": keyword.upper(),
                "manufacturer": manufacturer or "Unknown",
                "pin_count": api_specs.get("pin_count") or 0,
                "package_type": api_specs.get("package_type"),
                "description": api_specs.get("description") or f"{manufacturer} {keyword}",
                "voltage_min": api_specs.get("voltage_min"),
                "voltage_max": api_specs.get("voltage_max"),
                "operating_temp_min": api_specs.get("operating_temp_min"),
                "operating_temp_max": api_specs.get("operating_temp_max"),
                "dimension_length": None,
                "dimension_width": None,
                "dimension_height": None,
                "electrical_specs": {}
            }
            
            # Save API-only data to database
            saved_count = 0
            try:
                saved_count = await save_variants_to_db(
                    db=db,
                    variants=[api_variant],
                    datasheet_url=datasheet_url,
                    datasheet_path=str(local_pdf)
                )
                logger.info(f"Saved API-only variant to database: {keyword}")
            except Exception as db_error:
                logger.error(f"Database save failed for API-only variant: {db_error}")
            
            response_data = DigiKeySearchResponse(
                datasheet_path=str(local_pdf),
                manufacturer=manufacturer,
                parse_status="partial",
                total_variants=1,
                ic_variants=[ICVariant(**api_variant)],
                saved_to_db=saved_count,
                error=f"PDF parsing failed, using API data: {str(e)}"
            )
            
            return JSONResponse(
                content=json.loads(response_data.model_dump_json()),
                media_type="application/json"
            )

        response_data = DigiKeySearchResponse(
            datasheet_path=str(local_pdf),
            manufacturer=manufacturer,
            parse_status="error",
            total_variants=0,
            ic_variants=[],
            error=f"PDF parsing failed: {str(e)}"
        )
        
        return JSONResponse(
            content=json.loads(response_data.model_dump_json()),
            media_type="application/json"
        )
