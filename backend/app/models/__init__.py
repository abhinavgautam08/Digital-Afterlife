"""
Export all SQLAlchemy database models.
Phase 3: Speech-to-text, segments, background jobs, speaker consent and profiles.
"""
from backend.app.models.memory import Memory, MemoryPerson, MemoryTagAssociation
from backend.app.models.person import Person
from backend.app.models.transcript import Transcript, TranscriptSegment
from backend.app.models.tag import MemoryTag
from backend.app.models.transcription_job import TranscriptionJob
from backend.app.models.speaker import SpeakerConsent, SpeakerProfile
from backend.app.models.indexing_job import IndexingJob
from backend.app.models.storytelling import (
    StoryArtifact,
    ArtifactSourceMemory,
    TimelineEvent,
    TimelineEventMemory,
    MemoryCollection,
    CollectionMemory,
    RemembrancePage,
)

__all__ = [
    "Memory",
    "MemoryPerson",
    "MemoryTagAssociation",
    "Person",
    "Transcript",
    "TranscriptSegment",
    "MemoryTag",
    "TranscriptionJob",
    "SpeakerConsent",
    "SpeakerProfile",
    "IndexingJob",
    "StoryArtifact",
    "ArtifactSourceMemory",
    "TimelineEvent",
    "TimelineEventMemory",
    "MemoryCollection",
    "CollectionMemory",
    "RemembrancePage",
]
