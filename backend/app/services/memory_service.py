"""
Memory domain service for Phase 2.
Orchestrates multimedia ingestion, metadata extraction, advanced filtering,
patch updates, and consistent filesystem/database synchronization.
"""
import math
from typing import Optional, List, Tuple
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, desc, asc
from sqlalchemy.exc import IntegrityError
from backend.app.models.memory import Memory, MemoryPerson, MemoryTagAssociation
from backend.app.models.person import Person
from backend.app.models.tag import MemoryTag
from backend.app.core.security import sanitize_filename, compute_sha256
from backend.app.services.storage_service import storage_service
from backend.app.services.ingestion.metadata_extractor import extract_multimedia_metadata, IngestionResult
from backend.app.services.ingestion.validator import IngestionValidationError
from backend.app.schemas.memory import MemoryRead, MemoryListResponse, MemoryUpdate
from backend.app.core.logging import logger


class DuplicateMemoryError(Exception):
    """Raised when an identical memory file has already been ingested."""
    def __init__(self, message: str, existing_memory: Memory):
        super().__init__(message)
        self.existing_memory = existing_memory


class MemoryService:
    @staticmethod
    def _to_read_schema(memory: Memory) -> MemoryRead:
        """Converts SQLAlchemy model to MemoryRead schema with computed properties and transparent field decryption."""
        from backend.app.services.encryption.field_cipher import decrypt_field
        read_obj = MemoryRead.model_validate(memory)
        read_obj.has_thumbnail = bool(memory.thumbnail_path)
        read_obj.file_hash = memory.file_hash or memory.sha256_hash
        read_obj.description = decrypt_field(memory.description)
        read_obj.extracted_text = decrypt_field(memory.extracted_text)
        return read_obj

    @staticmethod
    def list_memories(
        db: Session,
        page: int = 1,
        size: int = 12,
        search: Optional[str] = None,
        memory_type: Optional[str] = None,
        person_id: Optional[str] = None,
        tag_name: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        sort_by: Optional[str] = "created_at_desc"
    ) -> MemoryListResponse:
        """
        Lists memories with pagination, text search across title/description/extracted_text,
        person filter, tag filter, date range filter, and custom sorting.
        """
        query = db.query(Memory)

        # 1. Filter by memory category
        if memory_type and memory_type.lower() != "all":
            query = query.filter(Memory.memory_type == memory_type.lower())

        # 2. Filter by associated person
        if person_id and person_id.strip():
            query = query.join(MemoryPerson, Memory.id == MemoryPerson.memory_id).filter(
                MemoryPerson.person_id == person_id.strip()
            )

        # 3. Filter by tag name
        if tag_name and tag_name.strip():
            clean_tag = tag_name.strip().lower()
            query = query.join(MemoryTagAssociation, Memory.id == MemoryTagAssociation.memory_id).join(
                MemoryTag, MemoryTagAssociation.tag_id == MemoryTag.id
            ).filter(MemoryTag.name == clean_tag)

        # 4. Filter by date range (event_date or created_at)
        if date_from:
            query = query.filter(or_(Memory.event_date >= date_from, Memory.created_at >= date_from))
        if date_to:
            query = query.filter(or_(Memory.event_date <= date_to, Memory.created_at <= date_to))

        # 5. Search text across title, description, extracted document text, and location
        if search and search.strip():
            term = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    Memory.title.ilike(term),
                    Memory.description.ilike(term),
                    Memory.extracted_text.ilike(term),
                    Memory.location.ilike(term)
                )
            )

        total = query.distinct().count()
        total_pages = math.ceil(total / size) if total > 0 else 1
        page = max(1, page)
        offset = (page - 1) * size

        # 6. Sorting
        sort_map = {
            "created_at_desc": desc(Memory.created_at),
            "created_at_asc": asc(Memory.created_at),
            "event_date_desc": desc(func.coalesce(Memory.event_date, Memory.created_at)),
            "event_date_asc": asc(func.coalesce(Memory.event_date, Memory.created_at)),
            "title_asc": asc(Memory.title),
            "title_desc": desc(Memory.title),
        }
        order_clause = sort_map.get(sort_by, desc(Memory.created_at))

        items = query.distinct().order_by(order_clause).offset(offset).limit(size).all()

        return MemoryListResponse(
            items=[MemoryService._to_read_schema(item) for item in items],
            total=total,
            page=page,
            size=size,
            total_pages=total_pages
        )

    @staticmethod
    def get_memory_by_id(db: Session, memory_id: str) -> Optional[Memory]:
        """Fetch a single memory by ID."""
        return db.query(Memory).filter(Memory.id == memory_id).first()

    @staticmethod
    def find_by_hash(db: Session, sha256_hash: str) -> Optional[Memory]:
        """Checks for existing memory matching the file's SHA-256 hash."""
        return db.query(Memory).filter(
            or_(Memory.sha256_hash == sha256_hash, Memory.file_hash == sha256_hash)
        ).first()

    @staticmethod
    def create_memory(
        db: Session,
        title: str,
        memory_type: str,
        original_filename: str,
        content_type: str,
        file_bytes: bytes,
        description: Optional[str] = None,
        event_date: Optional[datetime] = None,
        location: Optional[str] = None,
        privacy_level: str = "private",
        person_ids: Optional[List[str]] = None,
        tags: Optional[List[str]] = None
    ) -> Memory:
        """
        Executes the Phase 2 multimedia ingestion pipeline:
        1. Validates magic signatures & MIME type.
        2. Computes SHA-256 and blocks duplicates.
        3. Extracts metadata (dimensions, duration, text, thumbnails, capture date).
        4. Saves file in categorized folder.
        5. Saves SQLite record and associates people and tags.
        6. Guarantees filesystem/database consistency on failure.
        """
        clean_original = sanitize_filename(original_filename)

        # 1. Pre-check for duplicate via SHA-256 before generating derivative thumbnails
        early_hash = compute_sha256(file_bytes)
        existing = MemoryService.find_by_hash(db, early_hash)
        if existing:
            raise DuplicateMemoryError(
                f"A memory with identical content already exists: '{existing.title}'.",
                existing
            )

        # 2. Run multimedia extraction and validation
        ingest_res: IngestionResult = extract_multimedia_metadata(
            file_bytes=file_bytes,
            original_filename=clean_original,
            declared_mime=content_type
        )

        # Normalize memory category
        valid_types = {"photograph", "audio", "video", "document", "story"}
        target_type = memory_type.lower() if memory_type.lower() in valid_types else "document"

        # 3. Store file locally inside category folder
        stored_name, path_str, actual_size, _ = storage_service.save_file(
            content=file_bytes,
            original_filename=clean_original,
            memory_type=target_type
        )

        try:
            # Prefer user-provided event date; fallback to original capture date from EXIF if available
            effective_date = event_date or ingest_res.original_created_at

            # 4. Construct SQLite Model with field-level encryption if vault is initialized and unlocked
            from backend.app.core.crypto import vault_key_manager
            from backend.app.services.encryption.field_cipher import encrypt_field

            stored_desc = description.strip() if description else None
            stored_extracted = ingest_res.extracted_text
            if vault_key_manager.is_initialized() and vault_key_manager.is_unlocked():
                stored_desc = encrypt_field(stored_desc)
                stored_extracted = encrypt_field(stored_extracted)

            memory = Memory(
                title=title.strip(),
                description=stored_desc,
                memory_type=target_type,
                original_filename=clean_original,
                stored_filename=stored_name,
                file_path=path_str,
                mime_type=ingest_res.canonical_mime,
                file_size=actual_size,
                sha256_hash=ingest_res.file_hash,
                file_hash=ingest_res.file_hash,
                width=ingest_res.width,
                height=ingest_res.height,
                duration_seconds=ingest_res.duration_seconds,
                extracted_text=stored_extracted,
                thumbnail_path=ingest_res.thumbnail_path,
                original_created_at=ingest_res.original_created_at,
                event_date=effective_date,
                location=location.strip() if location else None,
                privacy_level=privacy_level,
                processing_status="completed" if not ingest_res.processing_error else "failed",
                processing_error=ingest_res.processing_error
            )
            db.add(memory)
            db.flush()

            # 5. Link people associations
            if person_ids:
                for pid in person_ids:
                    if pid and db.query(Person).filter(Person.id == pid).first():
                        assoc = MemoryPerson(memory_id=memory.id, person_id=pid, association_type="tagged")
                        db.add(assoc)

            # 6. Link tags (create tag if not existing)
            if tags:
                for tag_name in tags:
                    tag_name_clean = tag_name.strip().lower()
                    if not tag_name_clean:
                        continue
                    tag_obj = db.query(MemoryTag).filter(MemoryTag.name == tag_name_clean).first()
                    if not tag_obj:
                        import uuid
                        tag_obj = MemoryTag(id=str(uuid.uuid4()), name=tag_name_clean)
                        db.add(tag_obj)
                        db.flush()
                    tag_assoc = MemoryTagAssociation(memory_id=memory.id, tag_id=tag_obj.id)
                    db.add(tag_assoc)

            db.commit()
            db.refresh(memory)

            # Phase 4: Trigger semantic vector indexing
            try:
                from backend.app.services.rag.indexing_service import indexing_service
                indexing_service.index_memory(db, memory.id)
            except Exception as ex:
                logger.warning(f"Initial indexing deferred for memory '{memory.id}': {ex}")

            return memory

        except Exception as e:
            # Transaction rollback and cleanup physical file so no orphans remain
            db.rollback()
            storage_service.delete_file(stored_name, thumbnail_path=ingest_res.thumbnail_path)
            logger.error(f"Failed to persist memory record, cleaned up storage: {e}")
            if isinstance(e, IntegrityError):
                existing_race = MemoryService.find_by_hash(db, ingest_res.file_hash)
                if existing_race:
                    raise DuplicateMemoryError(
                        f"A memory with identical content already exists: '{existing_race.title}'.",
                        existing_race
                    )
            raise e

    @staticmethod
    def update_memory(
        db: Session,
        memory_id: str,
        update_data: MemoryUpdate
    ) -> Optional[Memory]:
        """Updates memory metadata, people associations, and tags."""
        memory = db.query(Memory).filter(Memory.id == memory_id).first()
        if not memory:
            return None

        if update_data.title is not None and update_data.title.strip():
            memory.title = update_data.title.strip()
        if update_data.description is not None:
            raw_d = update_data.description.strip() if update_data.description else None
            from backend.app.core.crypto import vault_key_manager
            from backend.app.services.encryption.field_cipher import encrypt_field
            if raw_d and vault_key_manager.is_initialized() and vault_key_manager.is_unlocked():
                memory.description = encrypt_field(raw_d)
            else:
                memory.description = raw_d
        if update_data.event_date is not None:
            memory.event_date = update_data.event_date
        if update_data.location is not None:
            memory.location = update_data.location.strip() if update_data.location else None
        if update_data.privacy_level is not None:
            memory.privacy_level = update_data.privacy_level
        if update_data.memory_type is not None:
            memory.memory_type = update_data.memory_type.lower()

        # Update people associations if provided
        if update_data.person_ids is not None:
            db.query(MemoryPerson).filter(MemoryPerson.memory_id == memory.id).delete()
            for pid in update_data.person_ids:
                if pid and db.query(Person).filter(Person.id == pid).first():
                    assoc = MemoryPerson(memory_id=memory.id, person_id=pid, association_type="tagged")
                    db.add(assoc)

        # Update tags if provided
        if update_data.tags is not None:
            db.query(MemoryTagAssociation).filter(MemoryTagAssociation.memory_id == memory.id).delete()
            for tag_name in update_data.tags:
                tag_name_clean = tag_name.strip().lower()
                if not tag_name_clean:
                    continue
                tag_obj = db.query(MemoryTag).filter(MemoryTag.name == tag_name_clean).first()
                if not tag_obj:
                    import uuid
                    tag_obj = MemoryTag(id=str(uuid.uuid4()), name=tag_name_clean)
                    db.add(tag_obj)
                    db.flush()
                tag_assoc = MemoryTagAssociation(memory_id=memory.id, tag_id=tag_obj.id)
                db.add(tag_assoc)

        memory.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(memory)

        # Phase 4: Trigger semantic vector re-indexing
        try:
            from backend.app.services.rag.indexing_service import indexing_service
            indexing_service.index_memory(db, memory.id, force=True)
        except Exception as ex:
            logger.warning(f"Reindexing failed for memory '{memory.id}': {ex}")

        return memory

    @staticmethod
    def delete_memory(db: Session, memory_id: str) -> bool:
        """Deletes database record and associated physical file and thumbnail."""
        memory = db.query(Memory).filter(Memory.id == memory_id).first()
        if not memory:
            return False

        # Phase 4: Remove from vector store
        try:
            from backend.app.services.rag.indexing_service import indexing_service
            indexing_service.delete_memory_vectors(db, memory_id)
        except Exception as ex:
            logger.warning(f"Failed to delete vectors for memory '{memory_id}': {ex}")

        # Delete physical file and thumbnail
        storage_service.delete_file(memory.stored_filename, thumbnail_path=memory.thumbnail_path)

        # Remove from database (cascades transcripts, associations)
        db.delete(memory)
        db.commit()
        return True


memory_service = MemoryService()
