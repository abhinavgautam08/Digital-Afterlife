"""
Indexing Service for Digital Afterlife.
Coordinates text chunking, embedding generation, vector store synchronization,
and SQLite indexing job tracking.
Ensures vector storage remains derived, ephemeral, and fully rebuildable from SQLite.
"""
import hashlib
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.models.memory import Memory, MemoryPerson, MemoryTagAssociation
from backend.app.models.tag import MemoryTag
from backend.app.models.transcript import Transcript, TranscriptSegment
from backend.app.models.indexing_job import IndexingJob
from backend.app.services.rag.chunker import chunker, MemoryChunk
from backend.app.services.rag.embedding_engine import embedding_engine
from backend.app.services.rag.vector_store import vector_store
from backend.app.services.rag.model_manager import embedding_model_manager
from backend.app.services.encryption.field_cipher import decrypt_field


class IndexingService:

    @staticmethod
    def _compute_memory_content_hash(memory: Memory, tags: List[str], transcript_text: str = "") -> str:
        """Computes a deterministic content hash of all indexable memory contents."""
        hasher = hashlib.sha256()
        hasher.update((memory.title or "").encode("utf-8"))
        hasher.update((memory.description or "").encode("utf-8"))
        hasher.update((memory.extracted_text or "").encode("utf-8"))
        hasher.update((memory.location or "").encode("utf-8"))
        hasher.update((memory.memory_type or "").encode("utf-8"))
        if memory.event_date:
            hasher.update(str(memory.event_date).encode("utf-8"))
        for t in sorted(tags):
            hasher.update(t.encode("utf-8"))
        if transcript_text:
            hasher.update(transcript_text.encode("utf-8"))
        # Bind hash to the active embedding model to invalidate stale vectors across model version changes
        hasher.update(settings.EMBEDDING_DEFAULT_MODEL.encode("utf-8"))
        return hasher.hexdigest()

    @classmethod
    def index_memory(cls, db: Session, memory_id: str, force: bool = False) -> Dict[str, Any]:
        """
        Extracts chunks for a memory, computes embeddings, and updates the vector store.
        Skips indexing if content has not changed unless force=True.
        """
        memory = db.query(Memory).filter(Memory.id == memory_id).first()
        if not memory:
            raise ValueError(f"Memory with ID '{memory_id}' not found.")

        # 1. Gather associations
        tag_names = [
            t.name for t in db.query(MemoryTag)
            .join(MemoryTagAssociation, MemoryTag.id == MemoryTagAssociation.tag_id)
            .filter(MemoryTagAssociation.memory_id == memory_id).all()
        ]

        person_ids = [
            mp.person_id for mp in db.query(MemoryPerson)
            .filter(MemoryPerson.memory_id == memory_id).all()
        ]

        # 2. Gather transcripts if any
        transcripts = db.query(Transcript).filter(Transcript.memory_id == memory_id).all()
        all_transcript_text = "\n".join([t.transcript_text for t in transcripts if t.transcript_text])

        # 3. Content hash check for idempotency before changing job state
        current_hash = cls._compute_memory_content_hash(memory, tag_names, all_transcript_text)

        # Find or create IndexingJob
        job = db.query(IndexingJob).filter(IndexingJob.memory_id == memory_id).first()
        if not force and job and job.status == "completed" and job.content_hash == current_hash:
            logger.debug(f"Memory '{memory_id}' content unchanged. Skipping vector reindexing.")
            return {
                "memory_id": memory_id,
                "status": "skipped",
                "chunk_count": job.chunk_count,
                "message": "Content unchanged."
            }

        if not job:
            job = IndexingJob(memory_id=memory_id, status="indexing")
            db.add(job)
            db.flush()
        else:
            job.status = "indexing"
            job.error_message = None
            db.flush()

        try:

            # 4. Generate Chunks
            chunks: List[MemoryChunk] = []
            event_date_str = memory.event_date.isoformat() if memory.event_date else None

            # 4a. Metadata / Description summary chunk
            summary_parts = [f"Title: {memory.title}"]
            if memory.memory_type:
                summary_parts.append(f"Type: {memory.memory_type}")
            if memory.event_date:
                summary_parts.append(f"Date: {event_date_str}")
            if memory.location:
                summary_parts.append(f"Location: {memory.location}")
            if tag_names:
                summary_parts.append(f"Tags: {', '.join(tag_names)}")
            dec_desc = decrypt_field(memory.description)
            if dec_desc:
                summary_parts.append(f"Description: {dec_desc}")

            meta_text = "\n".join(summary_parts)
            meta_chunks = chunker.chunk_text(
                text=meta_text,
                memory_id=memory_id,
                source_type="metadata",
                original_filename=memory.original_filename,
                tags=tag_names,
                person_ids=person_ids,
                event_date=event_date_str
            )
            chunks.extend(meta_chunks)

            # 4b. Extracted document text chunks (for PDF, DOCX, TXT, MD)
            dec_extracted = decrypt_field(memory.extracted_text)
            if dec_extracted and dec_extracted.strip():
                doc_chunks = chunker.chunk_text(
                    text=dec_extracted,
                    memory_id=memory_id,
                    source_type="document",
                    original_filename=memory.original_filename,
                    tags=tag_names,
                    person_ids=person_ids,
                    event_date=event_date_str
                )
                chunks.extend(doc_chunks)

            # 4c. Transcript segment chunks
            for tr in transcripts:
                segments_db = db.query(TranscriptSegment).filter(
                    TranscriptSegment.transcript_id == tr.id
                ).order_by(TranscriptSegment.start_time.asc()).all()

                segments_dicts = [
                    {
                        "start_time": s.start_time,
                        "end_time": s.end_time,
                        "text": decrypt_field(s.text) or "",
                        "speaker_label": s.speaker_label
                    }
                    for s in segments_db
                ]

                tr_chunks = chunker.chunk_transcript(
                    segments=segments_dicts,
                    memory_id=memory_id,
                    transcript_id=tr.id,
                    original_filename=memory.original_filename,
                    tags=tag_names,
                    person_ids=person_ids,
                    event_date=event_date_str
                )
                chunks.extend(tr_chunks)

            if not chunks:
                job.status = "completed"
                job.chunk_count = 0
                job.content_hash = current_hash
                db.commit()
                return {"memory_id": memory_id, "status": "completed", "chunk_count": 0}

            # Guard: If model is not installed (and not in mock test fixture mode), do NOT generate mock vectors
            if not embedding_engine.is_semantic_available():
                logger.info(
                    f"Embedding model '{settings.EMBEDDING_DEFAULT_MODEL}' is not installed. "
                    f"Skipping vector embedding generation for memory '{memory_id}' (operating in keyword-only fallback mode)."
                )
                job.status = "deferred_missing_model"
                job.chunk_count = 0
                job.content_hash = current_hash
                job.error_message = (
                    f"Embedding model '{settings.EMBEDDING_DEFAULT_MODEL}' not installed. "
                    "Memory remains fully searchable via keyword search."
                )
                job.updated_at = datetime.now(timezone.utc)
                db.commit()
                return {
                    "memory_id": memory_id,
                    "status": "deferred_missing_model",
                    "chunk_count": 0,
                    "content_hash": current_hash,
                    "message": "Model not installed. Operating in keyword-only fallback mode."
                }

            # 5. Generate Vector Embeddings
            texts_to_embed = [c.text for c in chunks]
            engine = embedding_engine.get_engine()
            embeddings = engine.embed_documents(texts_to_embed)

            # 6. Synchronize ChromaDB: purge old vectors and upsert new
            vector_store.delete_by_memory_id(memory_id)
            vector_store.add_chunks(chunks, embeddings)

            # 7. Update Job Status in SQLite
            job.status = "completed"
            job.chunk_count = len(chunks)
            job.content_hash = current_hash
            job.error_message = None
            job.updated_at = datetime.now(timezone.utc)
            db.commit()

            logger.info(f"Successfully indexed memory '{memory_id}' with {len(chunks)} chunks.")
            return {
                "memory_id": memory_id,
                "status": "completed",
                "chunk_count": len(chunks),
                "content_hash": current_hash
            }

        except Exception as e:
            db.rollback()
            job.status = "failed"
            job.error_message = str(e)
            job.updated_at = datetime.now(timezone.utc)
            db.commit()
            logger.error(f"Failed to index memory '{memory_id}': {e}")
            raise

    @classmethod
    def delete_memory_vectors(cls, db: Session, memory_id: str) -> int:
        """Removes all indexed chunks from vector store and cleans up tracking job."""
        deleted_count = vector_store.delete_by_memory_id(memory_id)
        db.query(IndexingJob).filter(IndexingJob.memory_id == memory_id).delete()
        db.commit()
        return deleted_count

    @classmethod
    def rebuild_index(cls, db: Session) -> Dict[str, Any]:
        """Completely purges vector store and re-indexes all active memories in SQLite."""
        logger.info("Initiating full vector store rebuild...")
        vector_store.reset()

        # Reset indexing jobs
        db.query(IndexingJob).delete()
        db.commit()

        memories = db.query(Memory).all()
        total_memories = len(memories)
        success_count = 0
        total_chunks = 0
        errors: List[Dict[str, str]] = []

        for mem in memories:
            try:
                res = cls.index_memory(db, mem.id, force=True)
                success_count += 1
                total_chunks += res.get("chunk_count", 0)
            except Exception as e:
                errors.append({"memory_id": mem.id, "error": str(e)})

        logger.info(
            f"Index rebuild complete: {success_count}/{total_memories} memories indexed, "
            f"{total_chunks} vector chunks."
        )
        return {
            "status": "completed" if not errors else "completed_with_errors",
            "total_memories": total_memories,
            "indexed_memories": success_count,
            "total_chunks": total_chunks,
            "errors": errors
        }

    @classmethod
    def retry_failed_jobs(cls, db: Session) -> Dict[str, Any]:
        """Retries all indexing jobs currently in 'failed' status."""
        failed_jobs = db.query(IndexingJob).filter(IndexingJob.status == "failed").all()
        retried = 0
        succeeded = 0
        errors = []

        for job in failed_jobs:
            retried += 1
            try:
                cls.index_memory(db, job.memory_id, force=True)
                succeeded += 1
            except Exception as e:
                errors.append({"memory_id": job.memory_id, "error": str(e)})

        return {
            "retried_count": retried,
            "succeeded_count": succeeded,
            "failed_count": len(errors),
            "errors": errors
        }

    @classmethod
    def get_index_status(cls, db: Session) -> Dict[str, Any]:
        """Returns comprehensive status of SQLite indexing jobs and ChromaDB vectors."""
        total_memories = db.query(Memory).count()
        completed_jobs = db.query(IndexingJob).filter(IndexingJob.status == "completed").count()
        failed_jobs = db.query(IndexingJob).filter(IndexingJob.status == "failed").count()
        queued_jobs = db.query(IndexingJob).filter(IndexingJob.status.in_(["queued", "indexing"])).count()

        vs_status = vector_store.get_status()
        emb_models = embedding_model_manager.list_models()
        default_model_status = next(
            (m for m in emb_models if m["is_default"]),
            {"installed": False, "available": False, "name": settings.EMBEDDING_DEFAULT_MODEL}
        )

        semantic_avail = embedding_engine.is_semantic_available()
        engine_loaded = embedding_engine._instance is not None and not embedding_engine.is_mock_enabled()
        fallback_mode = "real_semantic" if semantic_avail else "keyword_only"

        return {
            "total_memories": total_memories,
            "indexed_memories": completed_jobs,
            "failed_jobs": failed_jobs,
            "pending_jobs": queued_jobs,
            "vector_store": vs_status,
            "embedding_model": default_model_status,
            "is_synchronized": (completed_jobs == total_memories and failed_jobs == 0 and queued_jobs == 0),
            "semantic_available": semantic_avail,
            "keyword_available": True,
            "vector_store_available": vs_status.get("available", False),
            "embedding_model_name": settings.EMBEDDING_DEFAULT_MODEL,
            "embedding_model_loaded": engine_loaded,
            "fallback_mode": fallback_mode,
        }


indexing_service = IndexingService()
