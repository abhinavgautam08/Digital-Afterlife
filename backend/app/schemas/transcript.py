"""
Pydantic schemas for Transcript and TranscriptSegment entities.
Phase 3: Timestamped segments, speaker attribution, and transcript editing.
"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class TranscriptSegmentBase(BaseModel):
    start_time: float
    end_time: float
    text: str
    speaker_label: str = "Speaker 1"
    speaker_id: Optional[str] = None
    confidence: Optional[float] = None
    segment_order: int = 0


class TranscriptSegmentRead(TranscriptSegmentBase):
    id: str
    transcript_id: str

    model_config = ConfigDict(from_attributes=True)


class TranscriptSegmentUpdate(BaseModel):
    id: Optional[str] = None
    text: Optional[str] = None
    speaker_label: Optional[str] = None
    speaker_id: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None


class TranscriptBase(BaseModel):
    language: str = "en"
    detected_language: Optional[str] = None
    model_name: Optional[str] = None
    processing_duration: Optional[float] = None
    transcript_text: str
    processing_status: str = "completed"


class TranscriptCreate(TranscriptBase):
    pass


class TranscriptUpdate(BaseModel):
    transcript_text: Optional[str] = None
    language: Optional[str] = None
    segments: Optional[List[TranscriptSegmentUpdate]] = None


class TranscriptRead(TranscriptBase):
    id: str
    memory_id: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    segments: List[TranscriptSegmentRead] = []

    model_config = ConfigDict(from_attributes=True)
