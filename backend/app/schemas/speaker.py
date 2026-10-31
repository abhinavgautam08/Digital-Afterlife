"""
Pydantic schemas for speaker consent and voice profiles.
Phase 3: Privacy-first biometric verification.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class SpeakerConsentCreate(BaseModel):
    consent_given: bool = True
    consent_notes: Optional[str] = None


class SpeakerConsentRead(BaseModel):
    id: str
    person_id: str
    consent_given: bool
    consent_notes: Optional[str] = None
    consent_date: datetime
    revoked_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class SpeakerProfileRead(BaseModel):
    id: str
    person_id: str
    sample_count: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SpeakerEnrollRequest(BaseModel):
    memory_id: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None

