"""
Transcript CRUD and segment editing API routes.
Phase 3: Fetching transcripts, editing segments, and updating speaker assignments.
"""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.logging import logger
from backend.app.database.session import get_db
from backend.app.models.transcript import Transcript, TranscriptSegment
from backend.app.models.memory import Memory
from backend.app.schemas.transcript import (
    TranscriptRead,
    TranscriptUpdate,
)
from backend.app.core.crypto import vault_key_manager
from backend.app.services.encryption.field_cipher import decrypt_field, encrypt_field

router = APIRouter(tags=["Transcripts"])


def _check_vault_unlocked():
    """Ensures transcript operations reject access while vault is locked."""
    if vault_key_manager.is_initialized() and not vault_key_manager.is_unlocked():
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="Vault is locked. Unlock the vault with your passphrase to access transcripts."
        )


def _format_transcript_read(transcript: Transcript) -> TranscriptRead:
    """Converts Transcript model to TranscriptRead with transparent field decryption."""
    read_obj = TranscriptRead.model_validate(transcript)
    read_obj.transcript_text = decrypt_field(transcript.transcript_text) or ""
    for seg in read_obj.segments:
        seg.text = decrypt_field(seg.text) or ""
    return read_obj


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@router.get("/memories/{memory_id}/transcript", response_model=TranscriptRead)
def get_memory_transcript(memory_id: str, db: Session = Depends(get_db)):
    """Retrieves the full transcript with timestamped segments for a specific memory."""
    _check_vault_unlocked()
    memory = db.query(Memory).filter(Memory.id == memory_id).first()
    if not memory:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Memory '{memory_id}' not found.",
        )

    transcript = db.query(Transcript).filter(Transcript.memory_id == memory_id).first()
    if not transcript:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No transcript found for memory '{memory_id}'.",
        )

    return _format_transcript_read(transcript)


@router.patch("/transcripts/{transcript_id}", response_model=TranscriptRead)
def update_transcript(
    transcript_id: str,
    update_in: TranscriptUpdate,
    db: Session = Depends(get_db),
):
    """
    Updates transcript text or individual segment fields (text, speaker_label, speaker_id).
    """
    _check_vault_unlocked()
    transcript = db.query(Transcript).filter(Transcript.id == transcript_id).first()
    if not transcript:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transcript with ID '{transcript_id}' not found.",
        )

    if update_in.transcript_text is not None:
        transcript.transcript_text = encrypt_field(update_in.transcript_text)

    if update_in.language is not None:
        transcript.language = update_in.language

    # Handle segment updates
    if update_in.segments is not None:
        for seg_update in update_in.segments:
            if not seg_update.id:
                continue
            seg = db.query(TranscriptSegment).filter(
                TranscriptSegment.id == seg_update.id,
                TranscriptSegment.transcript_id == transcript_id,
            ).first()
            if seg:
                if seg_update.text is not None:
                    seg.text = encrypt_field(seg_update.text)
                if seg_update.speaker_label is not None:
                    seg.speaker_label = seg_update.speaker_label
                if seg_update.speaker_id is not None:
                    seg.speaker_id = seg_update.speaker_id if seg_update.speaker_id != "" else None
                if seg_update.start_time is not None:
                    seg.start_time = seg_update.start_time
                if seg_update.end_time is not None:
                    seg.end_time = seg_update.end_time

    transcript.updated_at = utc_now()
    db.commit()
    db.refresh(transcript)

    logger.info(f"Updated transcript {transcript_id}.")
    return _format_transcript_read(transcript)


@router.delete("/transcripts/{transcript_id}")
def delete_transcript(transcript_id: str, db: Session = Depends(get_db)):
    """Deletes a transcript and all its associated segments."""
    _check_vault_unlocked()
    transcript = db.query(Transcript).filter(Transcript.id == transcript_id).first()
    if not transcript:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transcript with ID '{transcript_id}' not found.",
        )

    db.delete(transcript)
    db.commit()

    logger.info(f"Deleted transcript {transcript_id} and all its segments.")
    return {"success": True, "message": "Transcript deleted successfully."}

