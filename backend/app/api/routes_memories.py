"""
Memory vault API routes.
Phase 2: Enhanced with multimedia upload, thumbnail streaming, PATCH updates,
and multi-parameter filtering & dedicated search.
"""
from typing import Optional, List
import io
import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, status
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.database.session import get_db
from backend.app.schemas.memory import MemoryRead, MemoryListResponse, MemoryUpdate
from backend.app.services.memory_service import MemoryService, DuplicateMemoryError
from backend.app.services.storage_service import storage_service
from backend.app.services.ingestion.thumbnail_service import thumbnail_service
from backend.app.services.ingestion.validator import IngestionValidationError
from backend.app.core.security import SecurityValidationError
from backend.app.core.logging import logger

router = APIRouter(prefix="/memories", tags=["Memories"])


@router.get("/search", response_model=MemoryListResponse)
def search_memories(
    q: str = Query(..., min_length=1, description="Search term for title, description, or document text"),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=12, ge=1, le=100),
    memory_type: Optional[str] = Query(default=None),
    db: Session = Depends(get_db)
):
    """Dedicated search endpoint querying titles, descriptions, and extracted document text."""
    return MemoryService.list_memories(
        db=db,
        page=page,
        size=size,
        search=q,
        memory_type=memory_type
    )


@router.get("", response_model=MemoryListResponse)
def list_memories(
    page: int = Query(default=1, ge=1, description="Page number"),
    size: int = Query(default=12, ge=1, le=100, description="Page size"),
    search: Optional[str] = Query(default=None, description="Search term for title, description, text, location"),
    memory_type: Optional[str] = Query(default=None, description="Filter by type (photograph, audio, document, story, video, or all)"),
    person_id: Optional[str] = Query(default=None, description="Filter by associated person UUID"),
    tag: Optional[str] = Query(default=None, description="Filter by tag name"),
    date_from: Optional[datetime] = Query(default=None, description="Earliest event date"),
    date_to: Optional[datetime] = Query(default=None, description="Latest event date"),
    sort_by: Optional[str] = Query(default="created_at_desc", description="Sorting field and order"),
    db: Session = Depends(get_db)
):
    """Retrieves paginated memory vault items with advanced filtering and sorting."""
    return MemoryService.list_memories(
        db=db,
        page=page,
        size=size,
        search=search,
        memory_type=memory_type,
        person_id=person_id,
        tag_name=tag,
        date_from=date_from,
        date_to=date_to,
        sort_by=sort_by
    )


@router.post("", response_model=MemoryRead, status_code=status.HTTP_201_CREATED)
async def upload_memory(
    file: UploadFile = File(...),
    title: str = Form(..., min_length=1, max_length=255),
    memory_type: str = Form(..., description="photograph, audio, document, story, video"),
    description: Optional[str] = Form(default=None),
    event_date: Optional[str] = Form(default=None),
    location: Optional[str] = Form(default=None),
    privacy_level: str = Form(default="private"),
    person_ids: Optional[str] = Form(default=None, description="JSON array or comma-separated person UUIDs"),
    tags: Optional[str] = Form(default=None, description="Comma-separated tags"),
    db: Session = Depends(get_db)
):
    """
    Ingests and securely stores a new multimedia memory artifact.
    Validates magic numbers, detects MIME spoofing, prevents duplicate uploads via SHA-256,
    extracts metadata (dimensions, duration, text), and generates thumbnails.
    """
    parsed_date = None
    if event_date and event_date.strip():
        try:
            clean_date_str = event_date.strip().replace("Z", "+00:00")
            parsed_date = datetime.fromisoformat(clean_date_str)
        except Exception:
            try:
                parsed_date = datetime.strptime(event_date.strip(), "%Y-%m-%d")
            except Exception:
                logger.warning(f"Could not parse event_date '{event_date}', storing as None")

    parsed_person_ids: List[str] = []
    if person_ids and person_ids.strip():
        try:
            parsed_person_ids = json.loads(person_ids)
            if not isinstance(parsed_person_ids, list):
                parsed_person_ids = [str(person_ids).strip()]
        except Exception:
            parsed_person_ids = [pid.strip() for pid in person_ids.split(",") if pid.strip()]

    parsed_tags: List[str] = []
    if tags and tags.strip():
        parsed_tags = [t.strip() for t in tags.split(",") if t.strip()]

    try:
        max_allowed = settings.MAX_UPLOAD_SIZE_BYTES
        chunks = []
        total_bytes = 0
        chunk_size = 1024 * 1024  # 1 MB

        while True:
            chunk = await file.read(chunk_size)
            if not chunk:
                break
            total_bytes += len(chunk)
            if total_bytes > max_allowed:
                max_mb = max_allowed // (1024 * 1024)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"File size exceeds maximum allowed limit of {max_mb} MB."
                )
            chunks.append(chunk)

        content = b"".join(chunks)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not read uploaded file: {str(e)}"
        )

    try:
        memory = MemoryService.create_memory(
            db=db,
            title=title,
            memory_type=memory_type,
            original_filename=file.filename or "unknown_artifact",
            content_type=file.content_type or "application/octet-stream",
            file_bytes=content,
            description=description,
            event_date=parsed_date,
            location=location,
            privacy_level=privacy_level,
            person_ids=parsed_person_ids,
            tags=parsed_tags
        )
        return MemoryService._to_read_schema(memory)

    except (IngestionValidationError, SecurityValidationError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except DuplicateMemoryError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": str(e),
                "existing_memory_id": e.existing_memory.id,
                "existing_title": e.existing_memory.title
            }
        )
    except Exception as e:
        logger.error(f"Error during memory creation: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while preserving the memory."
        )


@router.get("/{memory_id}", response_model=MemoryRead)
def get_memory(memory_id: str, db: Session = Depends(get_db)):
    """Fetches full metadata for a specific memory item."""
    memory = MemoryService.get_memory_by_id(db, memory_id)
    if not memory:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory not found.")
    return MemoryService._to_read_schema(memory)


@router.patch("/{memory_id}", response_model=MemoryRead)
def update_memory(
    memory_id: str,
    update_data: MemoryUpdate,
    db: Session = Depends(get_db)
):
    """Updates metadata (title, description, event date, location, people, tags) for an existing memory."""
    memory = MemoryService.update_memory(db, memory_id, update_data)
    if not memory:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory not found.")
    return MemoryService._to_read_schema(memory)


@router.delete("/{memory_id}", status_code=status.HTTP_200_OK)
def delete_memory(memory_id: str, db: Session = Depends(get_db)):
    """Permanently deletes a memory, its physical file, and its thumbnail."""
    success = MemoryService.delete_memory(db, memory_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory not found.")
    return {"status": "success", "message": f"Memory {memory_id} deleted successfully."}


@router.get("/{memory_id}/file")
def get_memory_file(memory_id: str, db: Session = Depends(get_db)):
    """Streams the media file for preview or playback, transparently decrypting if encrypted."""
    memory = MemoryService.get_memory_by_id(db, memory_id)
    if not memory:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory not found.")

    from backend.app.core.crypto import VaultLockedError, vault_key_manager
    from backend.app.services.encryption.file_encryptor import file_encryptor

    try:
        path = storage_service.get_secure_path(memory.stored_filename, memory_type=memory.memory_type)
        if not path.exists():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found on disk.")

        if file_encryptor.is_encrypted_file(path):
            if not vault_key_manager.is_unlocked():
                raise HTTPException(
                    status_code=status.HTTP_423_LOCKED,
                    detail="Vault is locked. Unlock the vault with your passphrase to view this memory."
                )
            return StreamingResponse(
                storage_service.stream_file(memory.stored_filename, memory_type=memory.memory_type),
                media_type=memory.mime_type,
                headers={"Content-Disposition": f'inline; filename="{memory.original_filename}"'}
            )

        return FileResponse(
            path=str(path),
            media_type=memory.mime_type,
            filename=memory.original_filename
        )
    except VaultLockedError as e:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail=str(e))
    except SecurityValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{memory_id}/thumbnail")
def get_memory_thumbnail(memory_id: str, db: Session = Depends(get_db)):
    """Streams the optimized thumbnail image for the memory."""
    memory = MemoryService.get_memory_by_id(db, memory_id)
    if not memory:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory not found.")

    from backend.app.core.crypto import VaultLockedError, vault_key_manager
    from backend.app.services.encryption.file_encryptor import file_encryptor

    # 1. Try dedicated thumbnail file
    if memory.thumbnail_path:
        thumb_path = thumbnail_service.get_thumbnail_path(memory.thumbnail_path)
        if thumb_path and thumb_path.exists():
            if file_encryptor.is_encrypted_file(thumb_path):
                if not vault_key_manager.is_unlocked():
                    raise HTTPException(
                        status_code=status.HTTP_423_LOCKED,
                        detail="Vault is locked. Unlock vault to view thumbnails."
                    )
                dek = vault_key_manager.get_dek()
                with open(thumb_path, "rb") as fin:
                    decrypted_data = b"".join(file_encryptor.decrypt_stream(fin, dek))
                return StreamingResponse(io.BytesIO(decrypted_data), media_type="image/jpeg")

            return FileResponse(path=str(thumb_path), media_type="image/jpeg")

    # 2. Fallback to original image if artifact is a photograph
    if memory.memory_type == "photograph" or memory.mime_type.startswith("image/"):
        path = storage_service.get_secure_path(memory.stored_filename, memory_type=memory.memory_type)
        if path.exists():
            if file_encryptor.is_encrypted_file(path):
                if not vault_key_manager.is_unlocked():
                    raise HTTPException(
                        status_code=status.HTTP_423_LOCKED,
                        detail="Vault is locked. Unlock vault to view thumbnails."
                    )
                return StreamingResponse(
                    storage_service.stream_file(memory.stored_filename, memory_type=memory.memory_type),
                    media_type=memory.mime_type
                )
            return FileResponse(path=str(path), media_type=memory.mime_type)

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No thumbnail available for this memory.")
