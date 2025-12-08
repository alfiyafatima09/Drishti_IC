"""
Datasheet downloader module.
Re-exports from unified storage module for backwards compatibility.
"""
from services.datasheet_storage import (
    generate_hash,
    download_pdf_async as download_pdf,
    get_datasheet_filename,
    get_datasheet_path,
    get_storage_folder,
    datasheet_exists,
)

__all__ = [
    'generate_hash',
    'download_pdf',
    'get_datasheet_filename',
    'get_datasheet_path',
    'get_storage_folder',
    'datasheet_exists',
]
