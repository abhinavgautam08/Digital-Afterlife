"""
Pydantic schemas for Phase 5: Storytelling, Biographies, Timelines, Collections, and Remembrance Pages.
"""
from typing import List, Optional, Any, Dict
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class SourceMemoryInfo(BaseModel):
    memory_id: str
    title: str
    memory_type: str
    original_filename: str
    event_date: Optional[str] = None
    location: Optional[str] = None
    excerpt: Optional[str] = None
    evidence_classification: str = "documented_fact"  # documented_fact, generated_narrative, unverified_detail, unknown


class BiographySection(BaseModel):
    section_id: str
    section_title: str
    narrative: str
    evidence_classification: str = "documented_fact"
    source_memory_ids: List[str] = Field(default_factory=list)
    is_unknown: bool = False


# Biography
class BiographyGenerateRequest(BaseModel):
    person_id: str
    source_memory_ids: Optional[List[str]] = None
    length: str = Field(default="medium", pattern="^(short|medium|detailed)$")
    tone: str = Field(default="respectful", pattern="^(respectful|warm|factual|reflective)$")
    language: str = Field(default="en", pattern="^(en|hi|source_preserved)$")
    sections_to_include: Optional[List[str]] = None


# Story
class StoryGenerateRequest(BaseModel):
    person_id: str
    source_memory_ids: List[str] = Field(..., min_length=1)
    title: Optional[str] = None
    tone: str = Field(default="respectful", pattern="^(respectful|warm|factual|reflective)$")
    language: str = Field(default="en", pattern="^(en|hi|source_preserved)$")


# Timeline
class TimelineGenerateRequest(BaseModel):
    person_id: str
    source_memory_ids: Optional[List[str]] = None


class TimelineEventCreate(BaseModel):
    person_id: str
    artifact_id: Optional[str] = None
    title: str = Field(..., min_length=1, max_length=255)
    event_date: Optional[datetime] = None
    approximate_date: Optional[str] = None
    date_confidence: str = Field(default="approximate", pattern="^(exact|approximate|unknown)$")
    description: str = Field(..., min_length=1)
    verification_status: str = Field(default="user_confirmed", pattern="^(ai_suggested|user_confirmed)$")
    source_memory_ids: Optional[List[str]] = None
    order_index: int = 0


class TimelineEventUpdate(BaseModel):
    title: Optional[str] = None
    event_date: Optional[datetime] = None
    approximate_date: Optional[str] = None
    date_confidence: Optional[str] = Field(default=None, pattern="^(exact|approximate|unknown)$")
    description: Optional[str] = None
    verification_status: Optional[str] = Field(default=None, pattern="^(ai_suggested|user_confirmed)$")
    source_memory_ids: Optional[List[str]] = None
    order_index: Optional[int] = None


class TimelineEventResponse(BaseModel):
    id: str
    person_id: str
    artifact_id: Optional[str] = None
    title: str
    event_date: Optional[datetime] = None
    approximate_date: Optional[str] = None
    date_confidence: str
    description: str
    verification_status: str
    order_index: int
    source_memory_ids: List[str] = Field(default_factory=list)
    source_memories: List[SourceMemoryInfo] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Story Artifact CRUD
class StoryArtifactUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    approval_status: Optional[str] = Field(default=None, pattern="^(pending|approved|rejected)$")
    sections_json: Optional[str] = None


class StoryArtifactResponse(BaseModel):
    id: str
    person_id: str
    person_name: Optional[str] = None
    artifact_type: str
    title: str
    content: str
    sections_json: Optional[str] = None
    sections: List[BiographySection] = Field(default_factory=list)
    language: str
    tone: str
    model_name: Optional[str] = None
    generation_status: str
    approval_status: str
    evidence_coverage: float
    warning: Optional[str] = None
    source_memories: List[SourceMemoryInfo] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Remembrance Page
class RemembrancePageCreate(BaseModel):
    person_id: str
    biography_artifact_id: Optional[str] = None
    featured_photograph_id: Optional[str] = None
    user_personal_notes: Optional[str] = None


class RemembrancePageUpdate(BaseModel):
    biography_artifact_id: Optional[str] = None
    featured_photograph_id: Optional[str] = None
    user_personal_notes: Optional[str] = None


class RemembrancePageResponse(BaseModel):
    id: str
    person_id: str
    person_name: str
    person_relationship: Optional[str] = None
    biography_artifact_id: Optional[str] = None
    biography: Optional[StoryArtifactResponse] = None
    featured_photograph_id: Optional[str] = None
    featured_photograph: Optional[Dict[str, Any]] = None
    user_personal_notes: Optional[str] = None
    privacy_level: str = "private"
    stories: List[StoryArtifactResponse] = Field(default_factory=list)
    timeline_events: List[TimelineEventResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Collections
class CollectionCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    collection_type: str = Field(
        default="custom",
        pattern="^(childhood|family|education|career|celebrations|travel|milestones|custom)$"
    )
    person_id: Optional[str] = None
    cover_memory_id: Optional[str] = None
    memory_ids: Optional[List[str]] = None


class CollectionUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    collection_type: Optional[str] = Field(
        default=None,
        pattern="^(childhood|family|education|career|celebrations|travel|milestones|custom)$"
    )
    person_id: Optional[str] = None
    cover_memory_id: Optional[str] = None


class CollectionItemAdd(BaseModel):
    memory_id: str
    order_index: int = 0


class CollectionResponse(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    collection_type: str
    person_id: Optional[str] = None
    cover_memory_id: Optional[str] = None
    memories_count: int = 0
    memories: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
