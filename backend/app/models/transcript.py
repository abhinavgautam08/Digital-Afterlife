"""
Transcript and TranscriptSegment models for audio/video oral history preservation.
Phase 3: Timestamped segments, detected language, and speaker attribution.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Float, Integer
from sqlalchemy.orm import relationship

from backend.app.database.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Transcript(Base):
    __tablename__ = "transcripts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    memory_id = Column(
        String(36),
        ForeignKey("memories.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    language = Column(String(10), default="en", nullable=False)
    detected_language = Column(String(10), nullable=True)
    model_name = Column(String(50), nullable=True)
    processing_duration = Column(Float, nullable=True)
    transcript_text = Column(Text, nullable=False)
    processing_status = Column(String(50), default="completed", nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    memory = relationship("Memory", back_populates="transcripts")
    segments = relationship(
        "TranscriptSegment",
        back_populates="transcript",
        cascade="all, delete-orphan",
        order_by="TranscriptSegment.start_time"
    )


class TranscriptSegment(Base):
    __tablename__ = "transcript_segments"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    transcript_id = Column(
        String(36),
        ForeignKey("transcripts.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    start_time = Column(Float, nullable=False)
    end_time = Column(Float, nullable=False)
    text = Column(Text, nullable=False)
    speaker_label = Column(String(100), default="Speaker 1", nullable=False)
    speaker_id = Column(
        String(36),
        ForeignKey("people.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    confidence = Column(Float, nullable=True)
    segment_order = Column(Integer, default=0, nullable=False)

    # Relationships
    transcript = relationship("Transcript", back_populates="segments")
    speaker = relationship("Person")
