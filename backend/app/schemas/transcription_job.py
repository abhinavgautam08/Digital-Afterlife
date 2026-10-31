"""
Pydantic schemas for transcription background jobs and Whisper model info.
Phase 3: Asynchronous queue, progress telemetry, and model management.
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict


class TranscriptionJobCreate(BaseModel):
    model_name: str = "base"
    language: str = "auto"
    enable_diarization: bool = True


class TranscriptionJobRead(BaseModel):
    id: str
    memory_id: str
    status: str
    progress: float
    current_stage: str
    error_message: Optional[str] = None
    model_name: str
    language: str
    enable_diarization: bool
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class WhisperModelInfo(BaseModel):
    name: str
    description: str
    disk_size_mb: int
    actual_size_mb: float
    is_installed: bool
    is_downloading: bool
    download_progress: float
    recommended: bool
    local_path: Optional[str] = None


class ModelDownloadRequest(BaseModel):
    model_name: str
    force: bool = False


class TranscriptionEngineStatus(BaseModel):
    device: str
    compute_type: str
    cpu_threads: int
    queue_concurrency: int
    ffmpeg_available: bool
    pyav_available: bool
    models_installed_count: int
    models_directory: str
    active_jobs_count: int

