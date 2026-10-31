"""
Metadata Extractor and Ingestion Pipeline Orchestrator for Phase 2.
Coordinates format validation, media processing, thumbnail generation, and text extraction.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List
import uuid

from backend.app.core.security import compute_sha256
from backend.app.services.ingestion.validator import validate_file_content, IngestionValidationError
from backend.app.services.ingestion.image_processor import process_image, ImageProcessingError
from backend.app.services.ingestion.audio_processor import process_audio
from backend.app.services.ingestion.video_processor import process_video
from backend.app.services.ingestion.document_processor import process_document
from backend.app.core.logging import logger


@dataclass
class IngestionResult:
    detected_format: str
    canonical_mime: str
    file_hash: str
    width: Optional[int] = None
    height: Optional[int] = None
    duration_seconds: Optional[float] = None
    extracted_text: Optional[str] = None
    thumbnail_path: Optional[str] = None
    original_created_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    waveform_data: Optional[List[float]] = None
    processing_error: Optional[str] = None


def extract_multimedia_metadata(
    file_bytes: bytes,
    original_filename: str,
    declared_mime: str,
    uuid_name: Optional[str] = None
) -> IngestionResult:
    """
    Main entry point for Phase 2 multimedia ingestion.
    1. Validates magic signatures & guards against MIME spoofing.
    2. Dispatches to dedicated format processor.
    3. Computes SHA-256 integrity hash.
    4. Generates thumbnails and extracts searchable text safely.
    """
    # 1. Signature & safety validation
    detected_format, canonical_mime = validate_file_content(
        file_bytes, original_filename, declared_mime
    )

    # 2. SHA-256 Digest
    file_hash = compute_sha256(file_bytes)
    target_uuid = uuid_name or uuid.uuid4().hex

    result = IngestionResult(
        detected_format=detected_format,
        canonical_mime=canonical_mime,
        file_hash=file_hash
    )

    try:
        # 3. Media-specific processing
        if detected_format in ("jpeg", "png", "webp", "gif"):
            try:
                img_data = process_image(file_bytes, uuid_name=target_uuid)
            except ImageProcessingError as e:
                raise IngestionValidationError(str(e))
            result.width = img_data.get("width")
            result.height = img_data.get("height")
            result.thumbnail_path = img_data.get("thumbnail_path")
            result.original_created_at = img_data.get("original_created_at")
            result.metadata = img_data.get("metadata", {})

        elif detected_format in ("mp3", "wav", "ogg", "flac", "m4a"):
            audio_data = process_audio(file_bytes, file_format=detected_format)
            result.duration_seconds = audio_data.get("duration_seconds")
            result.waveform_data = audio_data.get("waveform")
            result.metadata = audio_data.get("metadata", {})

        elif detected_format in ("mp4", "mov", "webm"):
            video_data = process_video(file_bytes, file_format=detected_format, uuid_name=target_uuid)
            result.duration_seconds = video_data.get("duration_seconds")
            result.width = video_data.get("width")
            result.height = video_data.get("height")
            result.metadata = video_data.get("metadata", {})

        elif detected_format in ("pdf", "docx", "text"):
            doc_data = process_document(file_bytes, file_format=detected_format)
            result.extracted_text = doc_data.get("extracted_text")
            result.metadata = doc_data.get("metadata", {})

    except IngestionValidationError:
        raise
    except Exception as e:
        logger.error(f"Error extracting metadata for {original_filename}: {e}")
        result.processing_error = str(e)

    return result

