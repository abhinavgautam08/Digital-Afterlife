"""
Local Speech-to-Text and Diarization Subsystem.
Phase 3: faster-whisper, model management, audio conversion, diarization, and job queue.
"""
from backend.app.services.speech.model_manager import model_manager
from backend.app.services.speech.audio_converter import audio_converter
from backend.app.services.speech.transcription_engine import (
    transcription_engine,
    ModelNotInstalledError,
    ModelCorruptError,
)
from backend.app.services.speech.diarization_engine import diarization_engine
from backend.app.services.speech.speaker_service import (
    speaker_service,
    ConsentRequiredError,
)
from backend.app.services.speech.job_worker import transcription_worker

__all__ = [
    "model_manager",
    "audio_converter",
    "transcription_engine",
    "ModelNotInstalledError",
    "ModelCorruptError",
    "diarization_engine",
    "speaker_service",
    "ConsentRequiredError",
    "transcription_worker",
]

