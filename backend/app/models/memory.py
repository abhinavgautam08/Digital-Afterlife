"""
Memory and related association models.
Phase 2: Extended with multimedia metadata (width, height, duration, extracted_text, thumbnails, location).
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Text, Integer, Float, BigInteger, DateTime, ForeignKey, Index
)
from sqlalchemy.orm import relationship

from backend.app.database.base import Base


def utc_now() -> datetime:
    """Return current UTC datetime with timezone awareness."""
    return datetime.now(timezone.utc)


# Association table between Memory and Person
class MemoryPerson(Base):
    __tablename__ = "memory_people"

    memory_id = Column(
        String(36),
        ForeignKey("memories.id", ondelete="CASCADE"),
        primary_key=True
    )
    person_id = Column(
        String(36),
        ForeignKey("people.id", ondelete="CASCADE"),
        primary_key=True
    )
    association_type = Column(String(50), default="featured", nullable=False)

    # Relationships
    memory = relationship("Memory", back_populates="person_associations")
    person = relationship("Person", back_populates="memory_associations")


# Association table between Memory and Tag
class MemoryTagAssociation(Base):
    __tablename__ = "memory_tag_associations"

    memory_id = Column(
        String(36),
        ForeignKey("memories.id", ondelete="CASCADE"),
        primary_key=True
    )
    tag_id = Column(
        String(36),
        ForeignKey("memory_tags.id", ondelete="CASCADE"),
        primary_key=True
    )


class Memory(Base):
    __tablename__ = "memories"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    memory_type = Column(String(50), nullable=False, index=True)  # photograph, audio, video, document, story
    original_filename = Column(String(255), nullable=False)
    stored_filename = Column(String(255), nullable=False, unique=True, index=True)
    file_path = Column(String(500), nullable=False)
    mime_type = Column(String(100), nullable=False)
    file_size = Column(BigInteger, nullable=False)
    sha256_hash = Column(String(64), nullable=True, index=True)
    file_hash = Column(String(64), nullable=True, index=True)

    # Phase 2 Multimedia Metadata Extensions
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    extracted_text = Column(Text, nullable=True)
    thumbnail_path = Column(String(500), nullable=True)
    original_created_at = Column(DateTime, nullable=True, index=True)
    location = Column(String(255), nullable=True, index=True)
    processing_error = Column(Text, nullable=True)

    created_at = Column(DateTime, default=utc_now, nullable=False, index=True)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)
    event_date = Column(DateTime, nullable=True, index=True)
    privacy_level = Column(String(50), default="private", nullable=False)
    processing_status = Column(String(50), default="completed", nullable=False)

    # Relationships
    person_associations = relationship(
        "MemoryPerson",
        back_populates="memory",
        cascade="all, delete-orphan"
    )
    people = relationship(
        "Person",
        secondary="memory_people",
        viewonly=True
    )
    transcripts = relationship(
        "Transcript",
        back_populates="memory",
        cascade="all, delete-orphan"
    )
    tags = relationship(
        "MemoryTag",
        secondary="memory_tag_associations",
        back_populates="memories"
    )

    __table_args__ = (
        Index("ix_memories_type_created", "memory_type", "created_at"),
        Index("ix_memories_title_search", "title"),
    )
