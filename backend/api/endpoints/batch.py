"""Batch processing endpoints for folder uploads with intelligent routing."""
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
import os
import asyncio
import logging
import uuid
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import zipfile
import io
import tempfile

from core.database import get_db
from services.model_router import ModelRouter
from schemas.batch import BatchScanRequest, BatchScanResult, BatchProgress

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["Batch Processing"])

# Global storage for batch jobs (in production, use Redis/database)
batch_jobs = {}

# Directory for storing batch images persistently
BATCH_IMAGES_DIR = Path(__file__).parent.parent.parent / "scanned_images" / "batch"
BATCH_IMAGES_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/batch-scan", response_model=BatchScanResult)
async def batch_scan(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db)
) -> BatchScanResult:
    """
    Process multiple images in batch with intelligent model routing.

    Accepts multiple image files or a ZIP folder.
    Returns job ID for progress tracking.
    """
    try:
        # Generate unique job ID
        job_id = str(uuid.uuid4())

        # Create job-specific directory for persistent storage
        job_dir = BATCH_IMAGES_DIR / job_id
        job_dir.mkdir(parents=True, exist_ok=True)

        image_paths = []

        # Handle uploaded files
        for file in files:
            if file.filename.endswith('.zip'):
                # Extract ZIP file to temp, then copy images
                temp_dir = Path(tempfile.mkdtemp())
                zip_content = await file.read()
                zip_path = temp_dir / file.filename
                with open(zip_path, 'wb') as f:
                    f.write(zip_content)

                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)

                # Find all images in extracted folder and copy to job_dir
                for root, dirs, files_in_dir in os.walk(temp_dir):
                    for filename in files_in_dir:
                        if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
                            src_path = Path(root) / filename
                            # Use unique name to avoid collisions
                            unique_name = f"{uuid.uuid4().hex[:8]}_{filename}"
                            dest_path = job_dir / unique_name
                            shutil.copy2(src_path, dest_path)
                            image_paths.append(dest_path)
                
                # Clean up temp
                shutil.rmtree(temp_dir, ignore_errors=True)

            elif file.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
                # Save individual image to job directory
                safe_filename = Path(file.filename).name
                # Use unique prefix to avoid filename collisions
                unique_name = f"{uuid.uuid4().hex[:8]}_{safe_filename}"
                file_path = job_dir / unique_name
                
                with open(file_path, 'wb') as f:
                    content = await file.read()
                    f.write(content)
                image_paths.append(file_path)

        if not image_paths:
            raise HTTPException(status_code=400, detail="No valid images found in upload")

        # Limit batch size
        if len(image_paths) > 100:
            raise HTTPException(status_code=400, detail="Maximum 100 images per batch")

        # Initialize batch job
        batch_jobs[job_id] = {
            'status': 'processing',
            'total_images': len(image_paths),
            'processed_images': 0,
            'results': [],
            'start_time': datetime.now(),
            'image_paths': image_paths,
            'job_dir': job_dir
        }

        # Start background processing
        background_tasks.add_task(process_batch_job, job_id)

        return BatchScanResult(
            job_id=job_id,
            status="processing",
            total_images=len(image_paths),
            message=f"Batch processing started for {len(image_paths)} images"
        )

    except Exception as e:
        logger.error(f"Batch scan failed: {e}")
        raise HTTPException(status_code=500, detail=f"Batch processing failed: {str(e)}")


@router.get("/batch-progress/{job_id}", response_model=BatchProgress)
async def get_batch_progress(job_id: str) -> BatchProgress:
    """
    Get progress of a batch processing job.
    """
    if job_id not in batch_jobs:
        raise HTTPException(status_code=404, detail="Batch job not found")

    job = batch_jobs[job_id]

    return BatchProgress(
        job_id=job_id,
        status=job['status'],
        progress_percentage=(job['processed_images'] / job['total_images']) * 100 if job['total_images'] > 0 else 0,
        processed_images=job['processed_images'],
        total_images=job['total_images'],
        results=job['results'] if job['status'] == 'completed' else None,
        estimated_time_remaining=calculate_eta(job)
    )


async def process_batch_job(job_id: str):
    """
    Background task to process batch images.
    """
    try:
        job = batch_jobs[job_id]
        image_paths = job['image_paths']

        # Initialize model router
        router = ModelRouter()

        # Process images in batch
        results = await router.process_batch([str(path) for path in image_paths])

        # Update image paths in results to be relative for API serving
        for result in results:
            # Convert absolute path to job_id/filename format for API
            path = Path(result['image_path'])
            result['image_path'] = f"{job_id}/{path.name}"

        # Update job with results
        job['results'] = results
        job['processed_images'] = len(results)
        job['status'] = 'completed'

        # Don't delete files - keep them for viewing
        # Files in scanned_images/batch/{job_id}/ will persist

        logger.info(f"Batch job {job_id} completed: {len(results)} images processed")

    except Exception as e:
        logger.error(f"Batch job {job_id} failed: {e}")
        job = batch_jobs.get(job_id)
        if job:
            job['status'] = 'failed'
            job['error'] = str(e)


def calculate_eta(job: Dict[str, Any]) -> Optional[float]:
    """
    Calculate estimated time remaining for batch job.
    """
    if job['processed_images'] == 0 or job['status'] != 'processing':
        return None

    elapsed = (datetime.now() - job['start_time']).total_seconds()
    avg_time_per_image = elapsed / job['processed_images']
    remaining_images = job['total_images'] - job['processed_images']

    return avg_time_per_image * remaining_images


@router.get("/batch-images/{job_id}/{filename}")
async def get_batch_image(job_id: str, filename: str):
    """
    Serve an image from a batch job.
    """
    # Security: validate job_id format (UUID)
    try:
        uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job ID format")
    
    # Construct path safely
    image_path = BATCH_IMAGES_DIR / job_id / filename
    
    # Security: ensure path doesn't escape batch directory
    try:
        image_path.resolve().relative_to(BATCH_IMAGES_DIR.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not image_path.exists():
        raise HTTPException(status_code=404, detail="Image not found")
    
    # Determine media type
    suffix = image_path.suffix.lower()
    media_types = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.bmp': 'image/bmp',
    }
    media_type = media_types.get(suffix, 'application/octet-stream')
    
    return FileResponse(image_path, media_type=media_type)