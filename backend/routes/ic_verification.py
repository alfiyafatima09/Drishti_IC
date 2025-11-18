"""
IC verification routes for authenticity checking
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import Optional, List
import uuid

from models.database import get_db, IC, VerificationResult
from services.ic_verification import ICVerificationService
from config.settings import settings

router = APIRouter()
verification_service = ICVerificationService()


@router.post("/verify/ic")
async def verify_ic(
    background_tasks: BackgroundTasks,
    image_file: Optional[UploadFile] = File(None),
    image_path: Optional[str] = None,
    part_number: Optional[str] = None,
    manufacturer: Optional[str] = None,
    thorough_check: Optional[bool] = True,
    db: Session = Depends(get_db)
):
    """Verify IC authenticity from image"""

    
    if not image_file and not image_path:
        raise HTTPException(status_code=400, detail="Provide either image_file or image_path")

    try:
       
        verification_id = str(uuid.uuid4())

       
        if image_file:
            content = await image_file.read()
            result = await verification_service.verify_ic_from_image(
                content,
                filename=image_file.filename,
                part_number=part_number,
                manufacturer=manufacturer,
                thorough_check=thorough_check
            )
        else:
            result = await verification_service.verify_ic_from_path(
                image_path,
                part_number=part_number,
                manufacturer=manufacturer,
                thorough_check=thorough_check
            )

       
        ic = db.query(IC).filter_by(part_number=result.get("detected_part_number")).first()

        verification_result = VerificationResult(
            ic_id=ic.id if ic else None,
            detected_part_number=result.get("detected_part_number"),
            detected_manufacturer=result.get("detected_manufacturer"),
            detected_text=result.get("detected_text"),
            confidence_scores=result.get("confidence_scores"),
            logo_match_score=result.get("logo_match_score"),
            font_similarity_score=result.get("font_similarity_score"),
            marking_accuracy_score=result.get("marking_accuracy_score"),
            overall_confidence=result.get("overall_confidence"),
            is_genuine=result.get("is_genuine", False),
            authenticity_reasons=result.get("authenticity_reasons"),
            analysis_results=result.get("analysis_results"),
            processing_time_seconds=result.get("processing_time_seconds")
        )

        db.add(verification_result)
        db.commit()
        db.refresh(verification_result)

        result["verification_id"] = verification_result.id
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"IC verification failed: {str(e)}")


@router.get("/verify/results/{verification_id}")
async def get_verification_result(verification_id: int, db: Session = Depends(get_db)):
    """Get detailed verification results"""

    result = db.query(VerificationResult).filter_by(id=verification_id).first()
    if not result:
        raise HTTPException(status_code=404, detail="Verification result not found")

    return {
        "verification_id": result.id,
        "ic_id": result.ic_id,
        "detected_part_number": result.detected_part_number,
        "detected_manufacturer": result.detected_manufacturer,
        "detected_text": result.detected_text,
        "confidence_scores": result.confidence_scores,
        "logo_match_score": result.logo_match_score,
        "font_similarity_score": result.font_similarity_score,
        "marking_accuracy_score": result.marking_accuracy_score,
        "overall_confidence": result.overall_confidence,
        "is_genuine": result.is_genuine,
        "authenticity_reasons": result.authenticity_reasons,
        "analysis_results": result.analysis_results,
        "created_at": result.created_at.isoformat(),
        "processing_time_seconds": result.processing_time_seconds
    }


@router.get("/verify/ic/{part_number}")
async def get_ic_specifications(part_number: str, db: Session = Depends(get_db)):
    """Get specifications for a specific IC part number"""

    ic = db.query(IC).filter_by(part_number=part_number).first()
    if not ic:
        raise HTTPException(status_code=404, detail="IC not found in database")

    return {
        "part_number": ic.part_number,
        "manufacturer": ic.manufacturer.name if ic.manufacturer else None,
        "operating_voltage": {
            "min": ic.operating_voltage_min,
            "max": ic.operating_voltage_max,
            "unit": ic.operating_voltage_unit
        },
        "current_rating": {
            "value": ic.current_rating,
            "unit": ic.current_unit
        },
        "temperature_range": {
            "min": ic.temperature_min,
            "max": ic.temperature_max,
            "unit": ic.temperature_unit
        },
        "pin_count": ic.pin_count,
        "package_type": ic.package_type,
        "dimensions": ic.dimensions,
        "marking_specifications": ic.marking_specifications,
        "font_specifications": ic.font_specifications,
        "logo_requirements": ic.logo_requirements,
        "datasheet_url": ic.datasheet_url,
        "other_specs": ic.other_specs
    }


@router.post("/verify/batch")
async def batch_verify_ics(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    """Batch verify multiple ICs"""

    if len(files) > 10:  # Limit batch size
        raise HTTPException(status_code=400, detail="Maximum 10 files per batch")

    results = []
    for file in files:
        try:
            content = await file.read()
            result = await verification_service.verify_ic_from_image(content, filename=file.filename)
            results.append({
                "filename": file.filename,
                "result": result
            })
        except Exception as e:
            results.append({
                "filename": file.filename,
                "error": str(e)
            })

    return {"batch_results": results}


@router.get("/verify/manufacturers")
async def get_supported_manufacturers():
    """Get list of supported manufacturers"""

    return {
        "manufacturers": list(settings.supported_manufacturers.keys()),
        "details": settings.supported_manufacturers
    }


@router.get("/verify/history")
async def get_verification_history(
    limit: Optional[int] = 50,
    offset: Optional[int] = 0,
    genuine_only: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """Get verification history with optional filtering"""

    query = db.query(VerificationResult)

    if genuine_only is not None:
        query = query.filter_by(is_genuine=genuine_only)

    results = query.order_by(VerificationResult.created_at.desc()).offset(offset).limit(limit).all()

    return {
        "total": query.count(),
        "results": [
            {
                "id": r.id,
                "part_number": r.detected_part_number,
                "manufacturer": r.detected_manufacturer,
                "is_genuine": r.is_genuine,
                "overall_confidence": r.overall_confidence,
                "created_at": r.created_at.isoformat()
            }
            for r in results
        ]
    }
