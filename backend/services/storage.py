import uuid
from pathlib import Path
from typing import Tuple

from backend.core.config import settings


def save_image_file(file_bytes: bytes, original_filename: str) -> Tuple[str, Path]:
    """
    Save uploaded image file to storage.
    
    Args:
        file_bytes: Raw image file bytes
        original_filename: Original filename from upload
        
    Returns:
        Tuple of (image_id, file_path)
    """
    image_id = str(uuid.uuid4())
    ext = Path(original_filename).suffix.lower() or ".jpg"
    safe_ext = ext if len(ext) <= 10 else ".bin"
    
    target_filename = f"{image_id}{safe_ext}"
    target_path = settings.MEDIA_ROOT / target_filename
    
    with target_path.open("wb") as f:
        f.write(file_bytes)

    return image_id, target_path
