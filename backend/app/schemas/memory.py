"""
Pydantic schemas for Memory entity, updating, and pagination.
Phase 2: Enhanced multimedia metadata (width, height, duration, text, thumbnails, location).
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict

from backend.app.schemas.person import PersonSimple
from backend.app.schemas.transcript import TranscriptRead
from backend.app.schemas.tag import TagRead


class MemoryBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    memory_type: str = Field(..., description="photograph, audio, document, story, video")
    event_date: Optional[datetime] = None
    location: Optional[str] = Field(None, max_length=255)
    privacy_level: str = Field(default="private", description="private, family, archive")


class MemoryCreateForm(BaseModel):
    """Schema for form fields accompanying file upload."""
    title: str
    description: Optional[str] = None
    memory_type: str
    event_date: Optional[datetime] = None
    location: Optional[str] = None
    privacy_level: str = "private"
    person_ids: Optional[List[str]] = None
    tags: Optional[List[str]] = None


class MemoryUpdate(BaseModel):
    """Schema for updating memory metadata via PATCH."""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    memory_type: Optional[str] = None
    event_date: Optional[datetime] = None
    location: Optional[str] = None
    privacy_level: Optional[str] = None
    person_ids: Optional[List[str]] = None
    tags: Optional[List[str]] = None


class MemoryRead(MemoryBase):
    id: str
    original_filename: str
    stored_filename: str
    mime_type: str
    file_size: int
    sha256_hash: Optional[str] = None
    file_hash: Optional[str] = None
    processing_status: str

    # Phase 2 multimedia properties
    width: Optional[int] = None
    height: Optional[int] = None
    duration_seconds: Optional[float] = None
    extracted_text: Optional[str] = None
    thumbnail_path: Optional[str] = None
    original_created_at: Optional[datetime] = None
    has_thumbnail: bool = False

    created_at: datetime
    updated_at: datetime
    people: List[PersonSimple] = []
    tags: List[TagRead] = []
    transcripts: List[TranscriptRead] = []

    model_config = ConfigDict(from_attributes=True)


class MemoryListResponse(BaseModel):
    items: List[MemoryRead]
    total: int
    page: int
    size: int
    total_pages: int
