"""
Ingestion subsystem package export.
"""
from backend.app.services.ingestion.validator import (
    validate_file_content,
    detect_magic_format,
    IngestionValidationError,
)
from backend.app.services.ingestion.thumbnail_service import thumbnail_service, ThumbnailService
from backend.app.services.ingestion.image_processor import process_image, ImageProcessingError
from backend.app.services.ingestion.audio_processor import process_audio
from backend.app.services.ingestion.video_processor import process_video
from backend.app.services.ingestion.document_processor import process_document
from backend.app.services.ingestion.metadata_extractor import (
    extract_multimedia_metadata,
    IngestionResult,
)

__all__ = [
    "validate_file_content",
    "detect_magic_format",
    "IngestionValidationError",
    "thumbnail_service",
    "ThumbnailService",
    "process_image",
    "ImageProcessingError",
    "process_audio",
    "process_video",
    "process_document",
    "extract_multimedia_metadata",
    "IngestionResult",
]

