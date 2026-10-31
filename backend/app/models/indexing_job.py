"""
Indexing Job model for tracking semantic vector indexing operations.
Authoritative source of truth remains SQLite.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from backend.app.database.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class IndexingJob(Base):
    __tablename__ = "indexing_jobs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    memory_id = Column(
        String(36),
        ForeignKey("memories.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    status = Column(String(50), default="queued", nullable=False, index=True)  # queued, indexing, completed, failed
    chunk_count = Column(Integer, default=0, nullable=False)
    content_hash = Column(String(64), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    memory = relationship("Memory")

