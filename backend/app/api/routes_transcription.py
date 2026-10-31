"""
Transcription API routes.
Phase 3: Job dispatch, status polling, cancellation, model management, and engine health.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status, BackgroundTasks
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.database.session import get_db
from backend.app.models.memory import Memory
from backend.app.models.transcription_job import TranscriptionJob
from backend.app.schemas.transcription_job import (
    TranscriptionJobCreate,
    TranscriptionJobRead,
    WhisperModelInfo,
    ModelDownloadRequest,
    TranscriptionEngineStatus,
)
from backend.app.services.speech.model_manager import model_manager, SUPPORTED_MODELS
from backend.app.services.speech.job_worker import transcription_worker
from backend.app.services.speech.audio_converter import audio_converter
from backend.app.core.crypto import vault_key_manager

router = APIRouter(tags=["Transcription"])


def _check_vault_unlocked():
    """Ensures transcription job creation rejects access while vault is locked."""
    if vault_key_manager.is_initialized() and not vault_key_manager.is_unlocked():
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="Vault is locked. Unlock the vault to transcribe audio or video memories."
        )


@router.post(
    "/memories/{memory_id}/transcription",
    response_model=TranscriptionJobRead,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_transcription_job(
    memory_id: str,
    job_in: TranscriptionJobCreate,
    db: Session = Depends(get_db),
):
    """
    Submits an audio or video memory for local transcription.
    Returns 202 Accepted with the queued job metadata.
    """
    _check_vault_unlocked()
    memory = db.query(Memory).filter(Memory.id == memory_id).first()
    if not memory:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Memory with ID '{memory_id}' not found.",
        )

    if memory.memory_type not in ["audio", "video"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Memory of type '{memory.memory_type}' cannot be transcribed. Must be 'audio' or 'video'.",
        )

    if not memory.file_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Memory has no associated media file on disk.",
        )

    model_name = job_in.model_name.lower()
    if model_name not in SUPPORTED_MODELS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid model '{model_name}'. Supported models: {list(SUPPORTED_MODELS.keys())}",
        )

    # Privacy safeguard: Verify model is present locally before queueing
    if not model_manager.is_model_installed(model_name) and not settings.AUTO_DOWNLOAD_MODELS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Whisper model '{model_name}' is not installed locally. "
                f"To maintain privacy and prevent silent background downloads, "
                f"please install the model first via Settings or POST /api/transcription/models/download."
            ),
        )

    # Check if there is already an active job for this memory
    existing_active = db.query(TranscriptionJob).filter(
        TranscriptionJob.memory_id == memory_id,
        TranscriptionJob.status.in_(["queued", "preprocessing", "transcribing", "diarizing"]),
    ).first()

    if existing_active:
        return TranscriptionJobRead.model_validate(existing_active)

    # Create new queued job
    job = TranscriptionJob(
        memory_id=memory_id,
        status="queued",
        progress=0.0,
        current_stage="Queued",
        model_name=model_name,
        language=job_in.language,
        enable_diarization=job_in.enable_diarization,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # Notify worker
    transcription_worker.notify()

    logger.info(f"Enqueued transcription job {job.id} for memory '{memory.title}' ({model_name}, {job_in.language}).")
    return TranscriptionJobRead.model_validate(job)


@router.get("/transcription/jobs", response_model=List[TranscriptionJobRead])
def list_transcription_jobs(
    memory_id: Optional[str] = Query(None, description="Filter jobs by memory ID"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Lists transcription jobs ordered by recent creation."""
    query = db.query(TranscriptionJob)
    if memory_id:
        query = query.filter(TranscriptionJob.memory_id == memory_id)
    if status_filter:
        query = query.filter(TranscriptionJob.status == status_filter)

    jobs = query.order_by(TranscriptionJob.created_at.desc()).limit(limit).all()
    return [TranscriptionJobRead.model_validate(j) for j in jobs]


@router.get("/transcription/jobs/{job_id}", response_model=TranscriptionJobRead)
def get_transcription_job(job_id: str, db: Session = Depends(get_db)):
    """Retrieves current status and progress of a specific transcription job."""
    job = db.query(TranscriptionJob).filter(TranscriptionJob.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transcription job with ID '{job_id}' not found.",
        )
    return TranscriptionJobRead.model_validate(job)


@router.post("/transcription/jobs/{job_id}/cancel", response_model=TranscriptionJobRead)
def cancel_transcription_job(job_id: str, db: Session = Depends(get_db)):
    """Cancels a pending or active transcription job."""
    job = db.query(TranscriptionJob).filter(TranscriptionJob.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transcription job with ID '{job_id}' not found.",
        )

    if job.status in ["completed", "failed", "cancelled"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel job in '{job.status}' state.",
        )

    job.status = "cancelled"
    job.current_stage = "Cancelled by user"
    from datetime import datetime, timezone
    job.completed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(job)

    transcription_worker.cancel_job(job_id)
    return TranscriptionJobRead.model_validate(job)


@router.get("/transcription/models", response_model=List[WhisperModelInfo])
def list_models():
    """Lists supported Whisper models with local installation and download status."""
    return [WhisperModelInfo(**m) for m in model_manager.list_models()]


@router.post("/transcription/models/download", status_code=status.HTTP_202_ACCEPTED)
def trigger_model_download(
    request: ModelDownloadRequest,
    background_tasks: BackgroundTasks,
):
    """
    Explicitly triggers download of a Whisper model into local offline storage.
    Will NOT block if dispatched as a background task.
    """
    model_name = request.model_name.lower()
    if model_name not in SUPPORTED_MODELS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported model '{model_name}'. Supported: {list(SUPPORTED_MODELS.keys())}",
        )

    if model_manager.is_model_installed(model_name) and not request.force:
        return {
            "status": "already_installed",
            "message": f"Model '{model_name}' is already installed locally.",
            "model_name": model_name,
        }

    # Execute download in background thread
    background_tasks.add_task(model_manager.download_model, model_name, request.force)

    return {
        "status": "downloading",
        "message": f"Download initiated for model '{model_name}'.",
        "model_name": model_name,
    }


@router.delete("/transcription/models/{model_name}")
def delete_model(model_name: str):
    """Deletes a local Whisper model to reclaim disk space."""
    model_name = model_name.lower()
    if not model_manager.is_model_installed(model_name):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model '{model_name}' is not installed locally.",
        )
    deleted = model_manager.delete_model(model_name)
    return {"success": deleted, "message": f"Model '{model_name}' deleted."}


@router.get("/transcription/status", response_model=TranscriptionEngineStatus)
def get_transcription_status(db: Session = Depends(get_db)):
    """Returns engine configuration, compute type, and queue telemetry."""
    active_jobs = db.query(TranscriptionJob).filter(
        TranscriptionJob.status.in_(["queued", "preprocessing", "transcribing", "diarizing"])
    ).count()

    installed_models = sum(1 for m in model_manager.list_models() if m["is_installed"])

    import av
    pyav_available = True

    return TranscriptionEngineStatus(
        device=settings.WHISPER_DEVICE,
        compute_type=settings.WHISPER_COMPUTE_TYPE,
        cpu_threads=settings.WHISPER_CPU_THREADS,
        queue_concurrency=settings.WHISPER_QUEUE_CONCURRENCY,
        ffmpeg_available=audio_converter.is_ffmpeg_cli_available(),
        pyav_available=pyav_available,
        models_installed_count=installed_models,
        models_directory=str(settings.WHISPER_MODELS_DIR),
        active_jobs_count=active_jobs,
    )
