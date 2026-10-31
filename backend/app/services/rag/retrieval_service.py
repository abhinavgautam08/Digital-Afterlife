"""
Retrieval Service for Digital Afterlife.
Provides:
  - Semantic similarity search via ChromaDB embeddings
  - Keyword-based exact search via SQLite
  - Hybrid retrieval with Reciprocal Rank Fusion (RRF)
  - Rich metadata filtering (date range, person, memory type, tags, language)
  - Deduplication and source diversification to prevent single-memory monopolization
  - Full multilingual support (English and Hindi)
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import or_

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.models.memory import Memory, MemoryPerson, MemoryTagAssociation
from backend.app.models.tag import MemoryTag
from backend.app.models.transcript import Transcript, TranscriptSegment
from backend.app.services.rag.embedding_engine import embedding_engine
from backend.app.services.rag.vector_store import vector_store
from backend.app.services.encryption.field_cipher import decrypt_field


class RetrievalService:

    @classmethod
    def _filter_matches(
        cls,
        item: Dict[str, Any],
        memory_obj: Optional[Memory],
        date_from: Optional[datetime],
        date_to: Optional[datetime],
        person_id: Optional[str],
        memory_type: Optional[str],
        tags: Optional[List[str]],
        transcript_language: Optional[str],
        db: Session
    ) -> bool:
        """Applies filters to a retrieved chunk candidate."""
        if not memory_obj:
            return False

        # Memory Type
        if memory_type and memory_obj.memory_type.lower() != memory_type.lower():
            return False

        # Date Range
        mem_date = memory_obj.event_date or memory_obj.created_at
        if mem_date and mem_date.tzinfo is not None:
            mem_date = mem_date.replace(tzinfo=None)
        d_from = date_from.replace(tzinfo=None) if date_from and date_from.tzinfo is not None else date_from
        d_to = date_to.replace(tzinfo=None) if date_to and date_to.tzinfo is not None else date_to

        if d_from and mem_date and mem_date < d_from:
            return False
        if d_to and mem_date and mem_date > d_to:
            return False

        # Person Filter
        if person_id:
            person_match = person_id in item.get("person_ids", [])
            if not person_match:
                # Double check database association
                assoc = db.query(MemoryPerson).filter(
                    MemoryPerson.memory_id == memory_obj.id,
                    MemoryPerson.person_id == person_id
                ).first()
                if not assoc:
                    return False

        # Tags Filter
        if tags:
            clean_tags = [t.lower().strip() for t in tags if t.strip()]
            item_tags = [t.lower().strip() for t in item.get("tags", [])]
            if clean_tags and not any(t in item_tags for t in clean_tags):
                return False

        # Transcript Language Filter
        if transcript_language and item.get("source_type") == "transcript":
            tr_id = item.get("transcript_id")
            if tr_id:
                tr = db.query(Transcript).filter(Transcript.id == tr_id).first()
                if tr and tr.language.lower() != transcript_language.lower():
                    return False

        return True

    @classmethod
    def _diversify_and_deduplicate(
        cls,
        candidates: List[Dict[str, Any]],
        top_k: int,
        max_per_memory: int = 2
    ) -> List[Dict[str, Any]]:
        """
        Enforces source diversity so a single large document or transcript does not monopolize results.
        Allows up to max_per_memory chunks from the same memory, unless total memories are fewer than top_k.
        """
        memory_counts: Dict[str, int] = {}
        diversified: List[Dict[str, Any]] = []

        # Pass 1: Add candidates respecting max_per_memory
        for cand in candidates:
            mem_id = cand["memory_id"]
            count = memory_counts.get(mem_id, 0)
            if count < max_per_memory:
                diversified.append(cand)
                memory_counts[mem_id] = count + 1
            if len(diversified) >= top_k:
                return diversified

        # Pass 2: If we still have room, add remaining top candidates
        if len(diversified) < top_k:
            for cand in candidates:
                if cand not in diversified:
                    diversified.append(cand)
                    if len(diversified) >= top_k:
                        break

        return diversified

    @classmethod
    def is_semantic_available(cls) -> bool:
        """Returns True if semantic search is available."""
        return embedding_engine.is_semantic_available()

    @classmethod
    def semantic_search(
        cls,
        db: Session,
        query: str,
        top_k: int = 5,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        person_id: Optional[str] = None,
        memory_type: Optional[str] = None,
        tags: Optional[List[str]] = None,
        transcript_language: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Performs pure semantic search via vector embeddings."""
        if not query or not query.strip():
            return []

        # Guard: If model weights are uninstalled, do not attempt semantic search or mock generation
        if not embedding_engine.is_semantic_available():
            logger.warning(
                "Semantic search requested but embedding model is not installed. "
                "Returning empty results. Production mode strictly forbids mock embedding fallback."
            )
            return []

        engine = embedding_engine.get_engine()
        query_vec = engine.embed_query(query.strip())

        # Retrieve a broader pool (top_k * 3) to allow for metadata filtering & diversification
        raw_results = vector_store.query(query_vec, top_k=top_k * 3)
        if not raw_results:
            return []

        # Fetch memories in bulk
        memory_ids = list({r["memory_id"] for r in raw_results if r.get("memory_id")})
        memories = {m.id: m for m in db.query(Memory).filter(Memory.id.in_(memory_ids)).all()}

        filtered: List[Dict[str, Any]] = []
        for r in raw_results:
            mem_obj = memories.get(r["memory_id"])
            if cls._filter_matches(
                r, mem_obj, date_from, date_to, person_id, memory_type, tags, transcript_language, db
            ):
                item = dict(r)
                item["memory_title"] = mem_obj.title
                item["memory_type"] = mem_obj.memory_type
                item["memory_date"] = (mem_obj.event_date or mem_obj.created_at).isoformat()
                filtered.append(item)

        # Sort by similarity descending
        filtered.sort(key=lambda x: x.get("similarity", 0.0), reverse=True)
        return cls._diversify_and_deduplicate(filtered, top_k)

    @classmethod
    def keyword_search(
        cls,
        db: Session,
        query: str,
        top_k: int = 5,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        person_id: Optional[str] = None,
        memory_type: Optional[str] = None,
        tags: Optional[List[str]] = None,
        transcript_language: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Performs lexical keyword matching across SQLite memory titles, extracted text, and transcript segments."""
        if not query or not query.strip():
            return []

        clean_q = query.strip()
        term = f"%{clean_q}%"

        # Search Memory table
        mem_query = db.query(Memory).filter(
            or_(
                Memory.title.ilike(term),
                Memory.description.ilike(term),
                Memory.extracted_text.ilike(term),
                Memory.location.ilike(term)
            )
        )
        if memory_type:
            mem_query = mem_query.filter(Memory.memory_type == memory_type.lower())
        if person_id:
            mem_query = mem_query.join(MemoryPerson).filter(MemoryPerson.person_id == person_id)
        if date_from:
            mem_query = mem_query.filter(or_(Memory.event_date >= date_from, Memory.created_at >= date_from))
        if date_to:
            mem_query = mem_query.filter(or_(Memory.event_date <= date_to, Memory.created_at <= date_to))

        matching_memories = mem_query.limit(top_k * 2).all()

        results: List[Dict[str, Any]] = []
        for mem in matching_memories:
            # Highlight excerpt
            dec_desc = decrypt_field(mem.description) if mem.description else None
            dec_text = decrypt_field(mem.extracted_text) if mem.extracted_text else None
            excerpt = dec_desc or (dec_text[:300] if dec_text else mem.title)
            results.append({
                "chunk_id": f"{mem.id}_keyword_0",
                "memory_id": mem.id,
                "memory_title": mem.title,
                "memory_type": mem.memory_type,
                "memory_date": (mem.event_date or mem.created_at).isoformat(),
                "source_type": "document" if mem.extracted_text else "description",
                "original_filename": mem.original_filename,
                "text": excerpt,
                "similarity": 0.85,  # Nominal score for keyword match
                "score": 0.85,
                "start_time": None,
                "end_time": None,
                "tags": [t.name for t in mem.tags] if mem.tags else [],
                "person_ids": [p.id for p in mem.people] if mem.people else [],
            })

        # Also search Transcript segments
        seg_query = db.query(TranscriptSegment).filter(TranscriptSegment.text.ilike(term))
        matching_segs = seg_query.limit(top_k * 2).all()
        for seg in matching_segs:
            tr = db.query(Transcript).filter(Transcript.id == seg.transcript_id).first()
            if not tr:
                continue
            mem = db.query(Memory).filter(Memory.id == tr.memory_id).first()
            if not mem:
                continue
            if transcript_language and tr.language.lower() != transcript_language.lower():
                continue

            results.append({
                "chunk_id": f"{mem.id}_tr_seg_{seg.id}",
                "memory_id": mem.id,
                "memory_title": mem.title,
                "memory_type": mem.memory_type,
                "memory_date": (mem.event_date or mem.created_at).isoformat(),
                "source_type": "transcript",
                "original_filename": mem.original_filename,
                "text": f"[{seg.speaker_label}]: {seg.text}",
                "similarity": 0.90,
                "score": 0.90,
                "transcript_id": tr.id,
                "start_time": seg.start_time,
                "end_time": seg.end_time,
                "speaker_label": seg.speaker_label,
                "tags": [t.name for t in mem.tags] if mem.tags else [],
                "person_ids": [p.id for p in mem.people] if mem.people else [],
            })

        return cls._diversify_and_deduplicate(results, top_k)

    @classmethod
    def hybrid_search(
        cls,
        db: Session,
        query: str,
        top_k: int = 5,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        person_id: Optional[str] = None,
        memory_type: Optional[str] = None,
        tags: Optional[List[str]] = None,
        transcript_language: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Combines Semantic search and Keyword search via Reciprocal Rank Fusion (RRF).
        If semantic model weights are uninstalled, falls back gracefully and explicitly to keyword-only mode.
        """
        if not embedding_engine.is_semantic_available():
            logger.info("Semantic model is uninstalled. Hybrid search explicitly falling back to keyword search.")
            kw_results = cls.keyword_search(
                db, query, top_k=top_k, date_from=date_from, date_to=date_to,
                person_id=person_id, memory_type=memory_type, tags=tags,
                transcript_language=transcript_language
            )
            for item in kw_results:
                item["retrieval_source"] = "keyword_only_fallback"
            return kw_results

        k_rrf = 60
        semantic_list = cls.semantic_search(
            db, query, top_k=top_k * 2, date_from=date_from, date_to=date_to,
            person_id=person_id, memory_type=memory_type, tags=tags,
            transcript_language=transcript_language
        )
        keyword_list = cls.keyword_search(
            db, query, top_k=top_k * 2, date_from=date_from, date_to=date_to,
            person_id=person_id, memory_type=memory_type, tags=tags,
            transcript_language=transcript_language
        )

        fused_scores: Dict[str, float] = {}
        items_map: Dict[str, Dict[str, Any]] = {}

        for rank, item in enumerate(semantic_list):
            cid = item["chunk_id"]
            items_map[cid] = item
            fused_scores[cid] = fused_scores.get(cid, 0.0) + (1.0 / (k_rrf + rank + 1))

        for rank, item in enumerate(keyword_list):
            cid = item["chunk_id"]
            if cid not in items_map:
                items_map[cid] = item
            fused_scores[cid] = fused_scores.get(cid, 0.0) + (1.0 / (k_rrf + rank + 1))

        # Re-rank combined candidates
        sorted_ids = sorted(fused_scores.keys(), key=lambda cid: fused_scores[cid], reverse=True)
        ranked_candidates = []
        for cid in sorted_ids:
            cand = dict(items_map[cid])
            cand["rrf_score"] = round(fused_scores[cid], 5)
            ranked_candidates.append(cand)

        return cls._diversify_and_deduplicate(ranked_candidates, top_k)


retrieval_service = RetrievalService()
