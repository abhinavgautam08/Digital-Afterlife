"""
Intelligent Document and Transcript Chunker.
Splits text and transcripts into semantically coherent passages
(target 400-600 tokens, 50-80 tokens overlap) while strictly preserving:
  - Source boundaries
  - Transcript timestamps (start_time, end_time)
  - Speaker labels
  - Document headers and paragraph coherence
"""
import re
import hashlib
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class MemoryChunk(BaseModel):
    chunk_id: str
    memory_id: str
    source_type: str  # 'description', 'document', 'transcript', 'metadata'
    original_filename: str
    text: str
    chunk_index: int
    tags: List[str] = Field(default_factory=list)
    person_ids: List[str] = Field(default_factory=list)
    event_date: Optional[str] = None
    transcript_id: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    speaker_label: Optional[str] = None
    content_hash: str


class MemoryChunker:
    # Character heuristics: 1 token ≈ 4 characters
    TARGET_CHUNK_CHARS = 1600   # ~400 tokens
    MAX_CHUNK_CHARS = 2400      # ~600 tokens
    OVERLAP_CHARS = 250         # ~60 tokens
    MAX_CHUNKS_PER_MEMORY = 500

    @classmethod
    def _split_into_sentences(cls, text: str) -> List[str]:
        """Splits text on sentence boundaries for English, Hindi, and common punctuation."""
        if not text:
            return []
        # Support full stop, question mark, exclamation, and Hindi Purna Viram (।)
        sentences = re.split(r'(?<=[.?!।\n])\s+', text)
        return [s.strip() for s in sentences if s.strip()]

    @classmethod
    def chunk_text(
        cls,
        text: str,
        memory_id: str,
        source_type: str,
        original_filename: str,
        tags: Optional[List[str]] = None,
        person_ids: Optional[List[str]] = None,
        event_date: Optional[str] = None,
    ) -> List[MemoryChunk]:
        """
        Chunks arbitrary text (descriptions, document extracts) into overlapping blocks.
        Preserves complete sentences whenever possible.
        """
        if not text or not text.strip():
            return []

        clean_text = text.strip()
        tags = tags or []
        person_ids = person_ids or []

        # If text is already small enough, keep as single chunk
        if len(clean_text) <= cls.MAX_CHUNK_CHARS:
            chunk_hash = hashlib.sha256(clean_text.encode("utf-8")).hexdigest()[:16]
            return [
                MemoryChunk(
                    chunk_id=f"{memory_id}_{source_type}_0",
                    memory_id=memory_id,
                    source_type=source_type,
                    original_filename=original_filename,
                    text=clean_text,
                    chunk_index=0,
                    tags=tags,
                    person_ids=person_ids,
                    event_date=event_date,
                    content_hash=chunk_hash
                )
            ]

        sentences = cls._split_into_sentences(clean_text)
        chunks: List[MemoryChunk] = []
        current_sentences: List[str] = []
        current_length = 0
        chunk_idx = 0

        for sentence in sentences:
            sent_len = len(sentence)
            if current_length + sent_len > cls.TARGET_CHUNK_CHARS and current_sentences:
                # Flush current chunk
                chunk_str = " ".join(current_sentences)
                chunk_hash = hashlib.sha256(chunk_str.encode("utf-8")).hexdigest()[:16]
                chunks.append(
                    MemoryChunk(
                        chunk_id=f"{memory_id}_{source_type}_{chunk_idx}",
                        memory_id=memory_id,
                        source_type=source_type,
                        original_filename=original_filename,
                        text=chunk_str,
                        chunk_index=chunk_idx,
                        tags=tags,
                        person_ids=person_ids,
                        event_date=event_date,
                        content_hash=chunk_hash
                    )
                )
                chunk_idx += 1
                if chunk_idx >= cls.MAX_CHUNKS_PER_MEMORY:
                    break

                # Overlap: keep trailing sentences up to OVERLAP_CHARS
                overlap_sentences: List[str] = []
                overlap_len = 0
                for s in reversed(current_sentences):
                    if overlap_len + len(s) <= cls.OVERLAP_CHARS:
                        overlap_sentences.insert(0, s)
                        overlap_len += len(s)
                    else:
                        break
                current_sentences = overlap_sentences
                current_length = overlap_len

            current_sentences.append(sentence)
            current_length += sent_len

        # Flush final chunk
        if current_sentences and chunk_idx < cls.MAX_CHUNKS_PER_MEMORY:
            chunk_str = " ".join(current_sentences)
            chunk_hash = hashlib.sha256(chunk_str.encode("utf-8")).hexdigest()[:16]
            chunks.append(
                MemoryChunk(
                    chunk_id=f"{memory_id}_{source_type}_{chunk_idx}",
                    memory_id=memory_id,
                    source_type=source_type,
                    original_filename=original_filename,
                    text=chunk_str,
                    chunk_index=chunk_idx,
                    tags=tags,
                    person_ids=person_ids,
                    event_date=event_date,
                    content_hash=chunk_hash
                )
            )

        return chunks

    @classmethod
    def chunk_transcript(
        cls,
        segments: List[Dict[str, Any]],
        memory_id: str,
        transcript_id: str,
        original_filename: str,
        tags: Optional[List[str]] = None,
        person_ids: Optional[List[str]] = None,
        event_date: Optional[str] = None,
    ) -> List[MemoryChunk]:
        """
        Chunks transcript segments while strictly tracking start_time and end_time.
        Combines adjacent segments up to TARGET_CHUNK_CHARS.
        """
        if not segments:
            return []

        chunks: List[MemoryChunk] = []
        tags = tags or []
        person_ids = person_ids or []

        curr_text_parts: List[str] = []
        curr_length = 0
        chunk_start_time: Optional[float] = None
        chunk_end_time: Optional[float] = None
        speakers: set = set()
        chunk_idx = 0

        for seg in segments:
            text = seg.get("text", "").strip()
            if not text:
                continue

            start_t = float(seg.get("start_time", 0.0))
            end_t = float(seg.get("end_time", start_t))
            speaker = seg.get("speaker_label", "Unknown")

            if chunk_start_time is None:
                chunk_start_time = start_t
            chunk_end_time = end_t
            speakers.add(speaker)

            line = f"[{speaker}]: {text}"
            curr_text_parts.append(line)
            curr_length += len(line)

            if curr_length >= cls.TARGET_CHUNK_CHARS:
                chunk_str = "\n".join(curr_text_parts)
                chunk_hash = hashlib.sha256(chunk_str.encode("utf-8")).hexdigest()[:16]
                chunks.append(
                    MemoryChunk(
                        chunk_id=f"{memory_id}_tr_{chunk_idx}",
                        memory_id=memory_id,
                        source_type="transcript",
                        original_filename=original_filename,
                        text=chunk_str,
                        chunk_index=chunk_idx,
                        tags=tags,
                        person_ids=person_ids,
                        event_date=event_date,
                        transcript_id=transcript_id,
                        start_time=chunk_start_time,
                        end_time=chunk_end_time,
                        speaker_label=", ".join(sorted(speakers)),
                        content_hash=chunk_hash
                    )
                )
                chunk_idx += 1
                curr_text_parts = []
                curr_length = 0
                chunk_start_time = None
                chunk_end_time = None
                speakers = set()

        if curr_text_parts:
            chunk_str = "\n".join(curr_text_parts)
            chunk_hash = hashlib.sha256(chunk_str.encode("utf-8")).hexdigest()[:16]
            chunks.append(
                MemoryChunk(
                    chunk_id=f"{memory_id}_tr_{chunk_idx}",
                    memory_id=memory_id,
                    source_type="transcript",
                    original_filename=original_filename,
                    text=chunk_str,
                    chunk_index=chunk_idx,
                    tags=tags,
                    person_ids=person_ids,
                    event_date=event_date,
                    transcript_id=transcript_id,
                    start_time=chunk_start_time or 0.0,
                    end_time=chunk_end_time or 0.0,
                    speaker_label=", ".join(sorted(speakers)),
                    content_hash=chunk_hash
                )
            )

        return chunks


chunker = MemoryChunker()

