"""
Digikey-related API endpoints.

Provides a POST endpoint to search Digikey by keyword, download the first
datasheet PDF found, parse it to extract IC specifications, and return the results.
"""
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from pathlib import Path
from typing import List, Optional, Dict, Any
import logging

from services.digikey import search_and_download_datasheet, DigiKeyException
from services.pdf_parser import parse_pdf
from core.config import settings

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
    error: Optional[str] = None


@router.post("/search", response_model=DigiKeySearchResponse)
async def digikey_search(request: DigiKeySearchRequest):
    """
    Search DigiKey for IC by keyword, download datasheet, and extract specifications.
    
    Args:
        request: Contains the search keyword (e.g., "lm358")
    
    Returns:
        DigiKeySearchResponse with datasheet path and extracted IC specifications
        including part numbers, pin counts, voltage ranges, temperature ranges, etc.
    """
    keyword = request.keyword.strip()
    if not keyword:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="keyword is required")

    try:
        result = search_and_download_datasheet(keyword)
        local_pdf = result["path"]
        manufacturer = result["manufacturer"]
    except DigiKeyException as e:
        logger.error("Digikey search/download error: %s", e)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))
    except Exception as e:
        logger.exception("Unexpected error in digikey_search")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    # Parse PDF to extract IC specifications
    try:
        parsed = parse_pdf(Path(local_pdf), manufacturer=manufacturer)
        
        # Convert to response model
        ic_variants = []
        for variant_data in parsed.get("ic_variants", []):
            ic_variants.append(ICVariant(**variant_data))
        
        return DigiKeySearchResponse(
            datasheet_path=str(local_pdf),
            manufacturer=parsed.get("manufacturer"),
            parse_status=parsed.get("status", "unknown"),
            total_variants=parsed.get("total_variants", 0),
            ic_variants=ic_variants,
            error=parsed.get("error")
        )
        
    except Exception as e:
        logger.exception("PDF parsing failed for %s", local_pdf)
        # Return partial response with error
        return DigiKeySearchResponse(
            datasheet_path=str(local_pdf),
            manufacturer=manufacturer,
            parse_status="error",
            total_variants=0,
            ic_variants=[],
            error=f"PDF parsing failed: {str(e)}"
        )
