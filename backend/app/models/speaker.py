"""
Speaker consent and voice profile models for privacy-first speaker identification.
Phase 3: Consent-based voice enrollment foundation.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Boolean, Integer
from sqlalchemy.orm import relationship

from backend.app.database.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class SpeakerConsent(Base):
    __tablename__ = "speaker_consents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    person_id = Column(
        String(36),
        ForeignKey("people.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )
    consent_given = Column(Boolean, default=False, nullable=False)
    consent_notes = Column(Text, nullable=True)
    consent_date = Column(DateTime, default=utc_now, nullable=False)
    revoked_at = Column(DateTime, nullable=True)

    # Relationships
    person = relationship("Person")


class SpeakerProfile(Base):
    __tablename__ = "speaker_profiles"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    person_id = Column(
        String(36),
        ForeignKey("people.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )
    voice_signature = Column(Text, nullable=False)  # JSON-serialized acoustic feature vector
    sample_count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    person = relationship("Person")

