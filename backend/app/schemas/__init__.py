"""
Pydantic schemas package export.
Phase 3: Extended with transcripts, segments, jobs, and speaker consent schemas.
"""
from backend.app.schemas.person import PersonCreate, PersonRead, PersonSimple
from backend.app.schemas.tag import TagCreate, TagUpdate, TagRead
from backend.app.schemas.memory import (
    MemoryRead,
    MemoryListResponse,
    MemoryCreateForm,
    MemoryUpdate,
)
from backend.app.schemas.transcript import (
    TranscriptCreate,
    TranscriptRead,
    TranscriptUpdate,
    TranscriptSegmentRead,
    TranscriptSegmentUpdate,
)
from backend.app.schemas.transcription_job import (
    TranscriptionJobCreate,
    TranscriptionJobRead,
    WhisperModelInfo,
    ModelDownloadRequest,
    TranscriptionEngineStatus,
)
from backend.app.schemas.speaker import (
    SpeakerConsentCreate,
    SpeakerConsentRead,
    SpeakerProfileRead,
    SpeakerEnrollRequest,
)
from backend.app.schemas.ai import AIStatusResponse, AIModelsResponse, ModelInfo
from backend.app.schemas.system import SystemStatusResponse, HealthResponse, StorageStatus, MemoryStats

__all__ = [
    "PersonCreate",
    "PersonRead",
    "PersonSimple",
    "TagCreate",
    "TagUpdate",
    "TagRead",
    "MemoryRead",
    "MemoryListResponse",
    "MemoryCreateForm",
    "MemoryUpdate",
    "TranscriptCreate",
    "TranscriptRead",
    "TranscriptUpdate",
    "TranscriptSegmentRead",
    "TranscriptSegmentUpdate",
    "TranscriptionJobCreate",
    "TranscriptionJobRead",
    "WhisperModelInfo",
    "ModelDownloadRequest",
    "TranscriptionEngineStatus",
    "SpeakerConsentCreate",
    "SpeakerConsentRead",
    "SpeakerProfileRead",
    "SpeakerEnrollRequest",
    "AIStatusResponse",
    "AIModelsResponse",
    "ModelInfo",
    "SystemStatusResponse",
    "HealthResponse",
    "StorageStatus",
    "MemoryStats",
]
