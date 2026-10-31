"""
TranscriptionJob model for asynchronous persistent speech-to-text processing.
Phase 3: Robust queue, restart recovery, cancellation, and progress tracking.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Float, Boolean
from sqlalchemy.orm import relationship

from backend.app.database.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class TranscriptionJob(Base):
    __tablename__ = "transcription_jobs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    memory_id = Column(
        String(36),
        ForeignKey("memories.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    status = Column(
        String(50),
        default="queued",
        nullable=False,
        index=True
    )  # queued, preprocessing, transcribing, diarizing, completed, failed, cancelled
    progress = Column(Float, default=0.0, nullable=False)
    current_stage = Column(String(100), default="Queued", nullable=False)
    error_message = Column(Text, nullable=True)

    model_name = Column(String(50), default="base", nullable=False)
    language = Column(String(10), default="auto", nullable=False)
    enable_diarization = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime, default=utc_now, nullable=False, index=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    memory = relationship("Memory")

