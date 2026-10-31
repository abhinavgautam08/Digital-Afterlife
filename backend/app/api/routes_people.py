"""
People directory API routes.
Phase 3: Extended with consent-based speaker voice profiles and biometric authorization.
"""
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.database.session import get_db
from backend.app.schemas.person import PersonCreate, PersonRead
from backend.app.schemas.memory import MemoryRead
from backend.app.schemas.speaker import (
    SpeakerConsentCreate,
    SpeakerConsentRead,
    SpeakerProfileRead,
    SpeakerEnrollRequest,
)
from backend.app.services.person_service import PersonService
from backend.app.services.speech.speaker_service import (
    speaker_service,
    ConsentRequiredError,
)
from backend.app.services.speech.audio_converter import audio_converter, SAMPLE_RATE_16K
from backend.app.models.memory import MemoryPerson, Memory
from backend.app.services.memory_service import MemoryService
from backend.app.core.crypto import vault_key_manager

router = APIRouter(prefix="/people", tags=["People"])


def _check_vault_unlocked():
    """Ensures biometric and memory operations reject access while vault is locked."""
    if vault_key_manager.is_initialized() and not vault_key_manager.is_unlocked():
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="Vault is locked. Unlock the vault to access personal memories or voice profiles."
        )


@router.get("", response_model=List[PersonRead])
def list_people(db: Session = Depends(get_db)):
    """Retrieves all registered family members or individuals."""
    return PersonService.list_people(db)


@router.post("", response_model=PersonRead, status_code=status.HTTP_201_CREATED)
def create_person(person_in: PersonCreate, db: Session = Depends(get_db)):
    """Registers a new family member or person."""
    person = PersonService.create_person(db, person_in)
    return PersonRead(
        id=person.id,
        full_name=person.full_name,
        relationship=person.relationship,
        biography=person.biography,
        created_at=person.created_at,
        memories_count=0
    )


@router.get("/{person_id}/memories", response_model=List[MemoryRead])
def get_person_memories(person_id: str, db: Session = Depends(get_db)):
    """Retrieves all memories associated with a specific person."""
    _check_vault_unlocked()
    person = PersonService.get_person_by_id(db, person_id)
    if not person:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Person not found.")

    associations = db.query(MemoryPerson).filter(MemoryPerson.person_id == person_id).all()
    memory_ids = [a.memory_id for a in associations]
    memories = db.query(Memory).filter(Memory.id.in_(memory_ids)).order_by(Memory.created_at.desc()).all()

    return [MemoryService._to_read_schema(m) for m in memories]


# --- Speaker Consent Endpoints ---

@router.get("/{person_id}/consent", response_model=Optional[SpeakerConsentRead])
def get_speaker_consent(person_id: str, db: Session = Depends(get_db)):
    """Retrieves the voice biometric consent status for a person."""
    person = PersonService.get_person_by_id(db, person_id)
    if not person:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Person not found.")

    consent = speaker_service.get_consent(db, person_id)
    if not consent:
        return None
    return SpeakerConsentRead.model_validate(consent)


@router.post("/{person_id}/consent", response_model=SpeakerConsentRead)
def record_speaker_consent(
    person_id: str,
    consent_in: SpeakerConsentCreate,
    db: Session = Depends(get_db)
):
    """
    Records or revokes explicit consent for biometric voice profiling.
    Revoking consent automatically purges any existing voice profile.
    """
    person = PersonService.get_person_by_id(db, person_id)
    if not person:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Person not found.")

    consent = speaker_service.record_consent(
        db,
        person_id=person_id,
        consent_given=consent_in.consent_given,
        consent_notes=consent_in.consent_notes
    )
    return SpeakerConsentRead.model_validate(consent)


# --- Speaker Voice Profile Endpoints ---

@router.get("/{person_id}/speaker-profile", response_model=Optional[SpeakerProfileRead])
def get_speaker_profile(person_id: str, db: Session = Depends(get_db)):
    """Retrieves metadata of the enrolled speaker voice profile."""
    person = PersonService.get_person_by_id(db, person_id)
    if not person:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Person not found.")

    profile = speaker_service.get_profile(db, person_id)
    if not profile:
        return None
    return SpeakerProfileRead.model_validate(profile)


@router.post(
    "/{person_id}/speaker-profile/enroll",
    response_model=SpeakerProfileRead,
    status_code=status.HTTP_201_CREATED
)
def enroll_speaker_profile(
    person_id: str,
    enroll_in: SpeakerEnrollRequest,
    db: Session = Depends(get_db)
):
    """
    Enrolls a biometric voice profile for a person from an existing audio memory.
    STRICT PRIVACY: Fails with 403 Forbidden if explicit consent has not been granted.
    """
    person = PersonService.get_person_by_id(db, person_id)
    if not person:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Person not found.")

    if not speaker_service.has_consent(db, person_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Biometric voice enrollment requires explicit prior consent. Please record consent first."
        )

    if not enroll_in.memory_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A valid memory_id containing audio is required for voice enrollment."
        )

    memory = db.query(Memory).filter(Memory.id == enroll_in.memory_id).first()
    if not memory or not memory.file_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source memory or file not found.")

    file_path = Path(memory.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source audio file not found on disk.")

    _check_vault_unlocked()
    from backend.app.services.encryption.file_encryptor import file_encryptor
    if file_encryptor.is_encrypted_file(file_path):
        from backend.app.services.storage_service import storage_service
        decrypted_bytes, _ = storage_service.read_file(file_path.name, memory_type=memory.memory_type)
        audio_data, duration = audio_converter.load_audio_as_float32(decrypted_bytes)
    else:
        audio_data, duration = audio_converter.load_audio_as_float32(file_path)

    if enroll_in.start_time is not None and enroll_in.end_time is not None:
        start_samp = max(0, int(enroll_in.start_time * SAMPLE_RATE_16K))
        end_samp = min(len(audio_data), int(enroll_in.end_time * SAMPLE_RATE_16K))
        if end_samp - start_samp > 1600:
            audio_data = audio_data[start_samp:end_samp]

    try:
        profile = speaker_service.enroll_speaker(db, person_id, audio_data)
        return SpeakerProfileRead.model_validate(profile)
    except ConsentRequiredError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Enrollment failed: {e}")


@router.delete("/{person_id}/speaker-profile")
def delete_speaker_profile(person_id: str, db: Session = Depends(get_db)):
    """Deletes an enrolled speaker voice profile and all biometric data."""
    person = PersonService.get_person_by_id(db, person_id)
    if not person:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Person not found.")

    deleted = speaker_service.delete_profile(db, person_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No speaker profile found to delete.")

    return {"success": True, "message": f"Speaker profile for {person.full_name} deleted."}
