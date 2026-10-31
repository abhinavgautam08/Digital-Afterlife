"""
Storytelling, Biographies, Timelines, Collections, and Remembrance Page models.
Phase 5: Evidence-grounded generation, artifact persistence, and memory curation.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Text, Integer, Float, DateTime, ForeignKey, Index, UniqueConstraint
)
from sqlalchemy.orm import relationship

from backend.app.database.base import Base


def utc_now() -> datetime:
    """Return current UTC datetime with timezone awareness."""
    return datetime.now(timezone.utc)


class ArtifactSourceMemory(Base):
    """
    Association between a StoryArtifact and the source Memories used as evidence.
    Tracks evidence classification (documented_fact, generated_narrative, unverified_detail, unknown).
    """
    __tablename__ = "artifact_source_memories"

    artifact_id = Column(
        String(36),
        ForeignKey("story_artifacts.id", ondelete="CASCADE"),
        primary_key=True
    )
    memory_id = Column(
        String(36),
        ForeignKey("memories.id", ondelete="CASCADE"),
        primary_key=True
    )
    relevance_note = Column(String(255), nullable=True)
    evidence_classification = Column(String(50), default="documented_fact", nullable=False)

    # Relationships
    artifact = relationship("StoryArtifact", back_populates="source_associations")
    memory = relationship("Memory")


class StoryArtifact(Base):
    """
    Persisted AI-generated or user-curated storytelling artifact:
    biography, memory story, timeline summary, or remembrance essay.
    """
    __tablename__ = "story_artifacts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    person_id = Column(
        String(36),
        ForeignKey("people.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    artifact_type = Column(String(50), nullable=False, index=True)  # biography, story, timeline, remembrance_page
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    sections_json = Column(Text, nullable=True)  # JSON-encoded structured sections
    language = Column(String(20), default="en", nullable=False)  # en, hi, source_preserved
    tone = Column(String(50), default="respectful", nullable=False)  # respectful, warm, factual, reflective
    model_name = Column(String(100), nullable=True)
    generation_status = Column(String(50), default="completed", nullable=False)  # completed, failed, draft
    approval_status = Column(String(50), default="pending", nullable=False)  # pending, approved, rejected
    evidence_coverage = Column(Float, default=1.0, nullable=False)
    warning = Column(Text, nullable=True)

    created_at = Column(DateTime, default=utc_now, nullable=False, index=True)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    person = relationship("Person")
    source_associations = relationship(
        "ArtifactSourceMemory",
        back_populates="artifact",
        cascade="all, delete-orphan"
    )
    source_memories = relationship(
        "Memory",
        secondary="artifact_source_memories",
        viewonly=True
    )


class TimelineEventMemory(Base):
    """Association between a TimelineEvent and supporting source Memories."""
    __tablename__ = "timeline_event_memories"

    event_id = Column(
        String(36),
        ForeignKey("timeline_events.id", ondelete="CASCADE"),
        primary_key=True
    )
    memory_id = Column(
        String(36),
        ForeignKey("memories.id", ondelete="CASCADE"),
        primary_key=True
    )

    event = relationship("TimelineEvent", back_populates="memory_associations")
    memory = relationship("Memory")


class TimelineEvent(Base):
    """
    Chronological milestone event in a person's life timeline.
    Grounded strictly in documented memories.
    """
    __tablename__ = "timeline_events"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    person_id = Column(
        String(36),
        ForeignKey("people.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    artifact_id = Column(
        String(36),
        ForeignKey("story_artifacts.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    title = Column(String(255), nullable=False)
    event_date = Column(DateTime, nullable=True, index=True)
    approximate_date = Column(String(100), nullable=True)  # e.g., "circa 1955", "Summer 1970", "Early Childhood"
    date_confidence = Column(String(50), default="approximate", nullable=False)  # exact, approximate, unknown
    description = Column(Text, nullable=False)
    verification_status = Column(String(50), default="ai_suggested", nullable=False)  # ai_suggested, user_confirmed
    order_index = Column(Integer, default=0, nullable=False)

    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    person = relationship("Person")
    artifact = relationship("StoryArtifact")
    memory_associations = relationship(
        "TimelineEventMemory",
        back_populates="event",
        cascade="all, delete-orphan"
    )
    source_memories = relationship(
        "Memory",
        secondary="timeline_event_memories",
        viewonly=True
    )


class CollectionMemory(Base):
    """Association between a MemoryCollection and a Memory record."""
    __tablename__ = "collection_memories"

    collection_id = Column(
        String(36),
        ForeignKey("memory_collections.id", ondelete="CASCADE"),
        primary_key=True
    )
    memory_id = Column(
        String(36),
        ForeignKey("memories.id", ondelete="CASCADE"),
        primary_key=True
    )
    order_index = Column(Integer, default=0, nullable=False)
    added_at = Column(DateTime, default=utc_now, nullable=False)

    collection = relationship("MemoryCollection", back_populates="item_associations")
    memory = relationship("Memory")


class MemoryCollection(Base):
    """
    User-curated thematic collection of memories
    (Childhood, Family, Education, Career, Celebrations, Travel, Milestones).
    References existing records without duplicating original files.
    """
    __tablename__ = "memory_collections"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    collection_type = Column(String(50), default="custom", nullable=False, index=True)
    person_id = Column(
        String(36),
        ForeignKey("people.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    cover_memory_id = Column(
        String(36),
        ForeignKey("memories.id", ondelete="SET NULL"),
        nullable=True
    )

    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    person = relationship("Person")
    cover_memory = relationship("Memory", foreign_keys=[cover_memory_id])
    item_associations = relationship(
        "CollectionMemory",
        back_populates="collection",
        cascade="all, delete-orphan",
        order_by="CollectionMemory.order_index"
    )
    memories = relationship(
        "Memory",
        secondary="collection_memories",
        viewonly=True
    )


class RemembrancePage(Base):
    """
    Private, locally stored remembrance page for a person.
    Contains approved photo, biography, selected memories, timeline, and personal notes.
    Strictly private; zero cloud publication or sharing.
    """
    __tablename__ = "remembrance_pages"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    person_id = Column(
        String(36),
        ForeignKey("people.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )
    biography_artifact_id = Column(
        String(36),
        ForeignKey("story_artifacts.id", ondelete="SET NULL"),
        nullable=True
    )
    featured_photograph_id = Column(
        String(36),
        ForeignKey("memories.id", ondelete="SET NULL"),
        nullable=True
    )
    user_personal_notes = Column(Text, nullable=True)
    privacy_level = Column(String(50), default="private", nullable=False)  # Strictly private

    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    person = relationship("Person")
    biography = relationship("StoryArtifact", foreign_keys=[biography_artifact_id])
    featured_photograph = relationship("Memory", foreign_keys=[featured_photograph_id])

