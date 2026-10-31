"""
Transcription Job Worker.
Manages persistent background transcription queue with strict concurrency = 1.
Recovers interrupted jobs on server restart, tracks granular progress, and supports cancellation.
"""
import asyncio
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.database.session import SessionLocal
from backend.app.models.memory import Memory
from backend.app.models.transcript import Transcript, TranscriptSegment
from backend.app.models.transcription_job import TranscriptionJob
from backend.app.services.speech.audio_converter import audio_converter
from backend.app.services.speech.diarization_engine import diarization_engine
from backend.app.services.speech.speaker_service import speaker_service
from backend.app.services.speech.transcription_engine import transcription_engine


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class TranscriptionJobWorker:
    """Sequential background worker for transcription jobs."""

    def __init__(self):
        self._lock = threading.Lock()
        self._is_running = False
        self._worker_thread: Optional[threading.Thread] = None
        self._wake_event = threading.Event()
        self._current_job_id: Optional[str] = None
        self.get_session = SessionLocal

    def start(self):
        """Starts the background worker thread."""
        with self._lock:
            if self._is_running:
                return
            self._is_running = True
            self.recover_interrupted_jobs()
            self._worker_thread = threading.Thread(target=self._run_loop, daemon=True, name="TranscriptionWorker")
            self._worker_thread.start()
            logger.info("TranscriptionJobWorker started with concurrency=1.")

    def stop(self):
        """Stops the worker thread."""
        with self._lock:
            self._is_running = False
            self._wake_event.set()

    def notify(self):
        """Notifies the worker that a new job is available."""
        self._wake_event.set()

    def recover_interrupted_jobs(self):
        """Recovers any jobs left in active states during previous server shutdown."""
        db = self.get_session()
        try:
            interrupted = db.query(TranscriptionJob).filter(
                TranscriptionJob.status.in_(["preprocessing", "transcribing", "diarizing"])
            ).all()
            for job in interrupted:
                logger.warning(f"Recovering interrupted transcription job {job.id}. Resetting status to 'queued'.")
                job.status = "queued"
                job.current_stage = "Queued (recovered after restart)"
                job.progress = 0.0
            db.commit()
        except Exception as e:
            logger.error(f"Error recovering interrupted jobs: {e}")
        finally:
            db.close()

    def cancel_job(self, job_id: str) -> bool:
        """Marks a job as cancelled. If currently processing, worker will abort."""
        db = self.get_session()
        try:
            job = db.query(TranscriptionJob).filter(TranscriptionJob.id == job_id).first()
            if not job:
                return False
            if job.status in ["completed", "failed", "cancelled"]:
                return False

            job.status = "cancelled"
            job.current_stage = "Cancelled by user"
            job.completed_at = utc_now()
            db.commit()
            logger.info(f"Transcription job {job_id} cancelled.")
            return True
        finally:
            db.close()

    def _run_loop(self):
        """Main worker execution loop."""
        while self._is_running:
            try:
                job_processed = self._process_next_job()
                if not job_processed:
                    # Wait for next notification or periodic poll (5 seconds)
                    self._wake_event.wait(timeout=5.0)
                    self._wake_event.clear()
            except Exception as e:
                logger.error(f"Unexpected error in TranscriptionWorker loop: {e}")
                time.sleep(2.0)

    def _process_next_job(self) -> bool:
        """Finds and executes the next queued job sequentially."""
        db = self.get_session()
        job: Optional[TranscriptionJob] = None
        try:
            job = db.query(TranscriptionJob).filter(
                TranscriptionJob.status == "queued"
            ).order_by(TranscriptionJob.created_at.asc()).first()

            if not job:
                return False

            self._current_job_id = job.id
            job.status = "preprocessing"
            job.started_at = utc_now()
            job.progress = 10.0
            job.current_stage = "Preparing audio for processing"
            db.commit()

            memory = db.query(Memory).filter(Memory.id == job.memory_id).first()
            if not memory:
                raise ValueError(f"Associated memory {job.memory_id} does not exist.")

            file_path = Path(memory.file_path) if memory.file_path else None
            if not file_path or not file_path.exists():
                raise FileNotFoundError(f"Media file not found at path: {memory.file_path}")

            # Check for cancellation
            db.refresh(job)
            if job.status == "cancelled":
                logger.info(f"Job {job.id} was cancelled before audio loading.")
                return True

            # 1. Preprocessing Stage (10% - 30%)
            logger.info(f"Job {job.id}: Converting audio for memory '{memory.title}'...")
            from backend.app.services.encryption.file_encryptor import file_encryptor
            if file_encryptor.is_encrypted_file(file_path):
                from backend.app.services.storage_service import storage_service
                decrypted_bytes, _ = storage_service.read_file(file_path.name, memory_type=memory.memory_type)
                audio_data, duration = audio_converter.load_audio_as_float32(decrypted_bytes)
            else:
                audio_data, duration = audio_converter.load_audio_as_float32(file_path)

            db.refresh(job)
            if job.status == "cancelled":
                logger.info(f"Job {job.id} cancelled after audio loading.")
                return True

            job.status = "transcribing"
            job.progress = 30.0
            job.current_stage = "Transcribing speech to text"
            db.commit()

            # 2. Transcription Stage (30% - 75%)
            def on_progress(p: float):
                # Check for mid-inference cancellation
                db.refresh(job)
                if job.status == "cancelled":
                    raise InterruptedError("Job cancelled during inference")
                job.progress = round(30.0 + p * 45.0, 1)
                db.commit()

            logger.info(f"Job {job.id}: Running Whisper ({job.model_name}) inference...")
            result = transcription_engine.transcribe(
                audio_source=audio_data,
                model_name=job.model_name,
                language=job.language,
                progress_callback=on_progress,
            )

            db.refresh(job)
            if job.status == "cancelled":
                logger.info(f"Job {job.id} cancelled after transcription.")
                return True

            segments = result["segments"]

            # 3. Speaker Diarization Stage (75% - 90%)
            if job.enable_diarization and segments:
                db.refresh(job)
                if job.status == "cancelled":
                    return True

                job.status = "diarizing"
                job.progress = 80.0
                job.current_stage = "Clustering speaker voices (experimental)"
                db.commit()

                logger.info(f"Job {job.id}: Running heuristic speaker clustering...")
                segments = diarization_engine.diarize_segments(
                    full_audio=audio_data,
                    segments=segments,
                )

            db.refresh(job)
            if job.status == "cancelled":
                logger.info(f"Job {job.id} cancelled before persistence.")
                return True

            # 4. Database Persistence (90% - 100%)
            job.progress = 92.0
            job.current_stage = "Saving transcript and segments"
            db.commit()

            # Upsert Transcript record
            transcript = db.query(Transcript).filter(Transcript.memory_id == memory.id).first()
            if not transcript:
                transcript = Transcript(
                    memory_id=memory.id,
                    language=job.language if job.language != "auto" else result["detected_language"],
                    detected_language=result["detected_language"],
                    model_name=job.model_name,
                    processing_duration=result["processing_duration"],
                    transcript_text=result["full_text"],
                    processing_status="completed",
                )
                db.add(transcript)
                db.flush()
            else:
                transcript.language = job.language if job.language != "auto" else result["detected_language"]
                transcript.detected_language = result["detected_language"]
                transcript.model_name = job.model_name
                transcript.processing_duration = result["processing_duration"]
                transcript.transcript_text = result["full_text"]
                transcript.processing_status = "completed"
                transcript.updated_at = utc_now()
                # Clear previous segments
                db.query(TranscriptSegment).filter(TranscriptSegment.transcript_id == transcript.id).delete()
                db.flush()

            # Persist Segments (Strict Privacy: Unknown speakers remain anonymous without auto-association)
            for idx, seg in enumerate(segments):
                segment_row = TranscriptSegment(
                    transcript_id=transcript.id,
                    start_time=seg["start"],
                    end_time=seg["end"],
                    text=seg["text"],
                    speaker_label=seg.get("speaker_label", "Speaker 1"),
                    speaker_id=None,  # User confirmation required; no automatic biometric binding
                    confidence=seg.get("confidence"),
                    segment_order=idx,
                )
                db.add(segment_row)

            # Update memory extracted text if empty
            if not memory.extracted_text and result["full_text"]:
                memory.extracted_text = result["full_text"][:2000]

            db.refresh(job)
            if job.status == "cancelled":
                logger.info(f"Job {job.id} cancelled before completion commit.")
                return True

            job.status = "completed"
            job.progress = 100.0
            job.current_stage = "Completed"
            job.completed_at = utc_now()
            db.commit()

            # Phase 4: Index newly created transcript in vector store
            try:
                from backend.app.services.rag.indexing_service import indexing_service
                indexing_service.index_memory(db, memory.id, force=True)
            except Exception as ex:
                logger.warning(f"Transcript indexing deferred for memory '{memory.id}': {ex}")

            logger.info(f"Transcription job {job.id} completed successfully for memory '{memory.title}'.")
            return True

        except InterruptedError:
            logger.info(f"Job {job.id if job else 'unknown'} interrupted via cancellation.")
            if job:
                db.refresh(job)
                job.status = "cancelled"
                job.current_stage = "Cancelled by user"
                job.completed_at = utc_now()
                db.commit()
            return True

        except Exception as e:
            logger.error(f"Error processing transcription job {job.id if job else 'unknown'}: {e}", exc_info=True)
            if job:
                db.refresh(job)
                if job.status != "cancelled":
                    job.status = "failed"
                    job.progress = 0.0
                    job.current_stage = "Failed"
                    job.error_message = str(e)
                    job.completed_at = utc_now()
                    db.commit()
            return True
        finally:
            self._current_job_id = None
            db.close()


transcription_worker = TranscriptionJobWorker()
