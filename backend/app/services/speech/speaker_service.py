"""
Speaker Consent and Voice Profile Service.
Phase 3: Privacy-first biometric management.
Ensures voice profiles can ONLY be created after explicit user consent is recorded.
Provides enrollment, verification, and complete deletion of voice signatures.
"""
import json
from datetime import datetime, timezone
from typing import Optional, Tuple, Dict, Any, List
import numpy as np
from sqlalchemy.orm import Session

from backend.app.core.logging import logger
from backend.app.models.person import Person
from backend.app.models.speaker import SpeakerConsent, SpeakerProfile
from backend.app.services.speech.diarization_engine import AcousticFeatureExtractor, SAMPLE_RATE_16K


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ConsentRequiredError(Exception):
    """Raised when an operation requiring speaker biometric consent is attempted without consent."""
    pass


class SpeakerService:
    """Manages explicit consent and biometric voice profiles."""

    def __init__(self, match_threshold: float = 0.85):
        self.match_threshold = match_threshold
        self.feature_extractor = AcousticFeatureExtractor()

    # --- Consent Management ---

    def get_consent(self, db: Session, person_id: str) -> Optional[SpeakerConsent]:
        """Retrieves consent record for a person."""
        return db.query(SpeakerConsent).filter(SpeakerConsent.person_id == person_id).first()

    def has_consent(self, db: Session, person_id: str) -> bool:
        """Checks if a person has active (non-revoked) consent for voice analysis."""
        consent = self.get_consent(db, person_id)
        return bool(consent and consent.consent_given and consent.revoked_at is None)

    def record_consent(
        self,
        db: Session,
        person_id: str,
        consent_given: bool = True,
        consent_notes: Optional[str] = None
    ) -> SpeakerConsent:
        """Records or updates explicit consent for a person."""
        person = db.query(Person).filter(Person.id == person_id).first()
        if not person:
            raise ValueError(f"Person with ID {person_id} not found.")

        consent = self.get_consent(db, person_id)
        if not consent:
            consent = SpeakerConsent(
                person_id=person_id,
                consent_given=consent_given,
                consent_notes=consent_notes,
                consent_date=utc_now(),
                revoked_at=None if consent_given else utc_now()
            )
            db.add(consent)
        else:
            consent.consent_given = consent_given
            consent.consent_notes = consent_notes or consent.consent_notes
            if consent_given:
                consent.consent_date = utc_now()
                consent.revoked_at = None
            else:
                consent.revoked_at = utc_now()

        db.commit()
        db.refresh(consent)
        logger.info(f"Recorded consent for Person '{person.full_name}' ({person_id}): consent_given={consent_given}")
        return consent

    def revoke_consent(self, db: Session, person_id: str) -> bool:
        """Revokes consent and automatically deletes the voice profile if one exists."""
        consent = self.get_consent(db, person_id)
        if not consent:
            return False

        consent.consent_given = False
        consent.revoked_at = utc_now()

        # Delete voice profile to uphold privacy compliance
        profile = db.query(SpeakerProfile).filter(SpeakerProfile.person_id == person_id).first()
        if profile:
            db.delete(profile)
            logger.info(f"Purged voice profile for Person {person_id} due to consent revocation.")

        db.commit()
        return True

    # --- Voice Profile Management ---

    def get_profile(self, db: Session, person_id: str) -> Optional[SpeakerProfile]:
        """Retrieves speaker profile for a person."""
        return db.query(SpeakerProfile).filter(SpeakerProfile.person_id == person_id).first()

    def enroll_speaker(
        self,
        db: Session,
        person_id: str,
        audio_samples: np.ndarray,
        sample_rate: int = SAMPLE_RATE_16K
    ) -> SpeakerProfile:
        """
        Enrolls a voice profile for a Person using an audio sample.
        STRICT REQUIREMENT: Explicit consent must have already been granted.
        """
        if not self.has_consent(db, person_id):
            raise ConsentRequiredError(
                f"Cannot enroll speaker profile: explicit consent has not been granted for Person {person_id}."
            )

        person = db.query(Person).filter(Person.id == person_id).first()
        if not person:
            raise ValueError(f"Person with ID {person_id} does not exist.")

        # Extract features
        features = self.feature_extractor.extract_features(audio_samples, sample_rate)
        signature_json = json.dumps(features.tolist())

        profile = self.get_profile(db, person_id)
        if not profile:
            profile = SpeakerProfile(
                person_id=person_id,
                voice_signature=signature_json,
                sample_count=1,
                created_at=utc_now(),
                updated_at=utc_now()
            )
            db.add(profile)
        else:
            # Average feature vector with existing profile
            existing_feats = np.array(json.loads(profile.voice_signature), dtype=np.float32)
            n = profile.sample_count
            updated_feats = (existing_feats * n + features) / (n + 1)
            updated_feats /= (np.linalg.norm(updated_feats) + 1e-9)

            profile.voice_signature = json.dumps(updated_feats.tolist())
            profile.sample_count += 1
            profile.updated_at = utc_now()

        db.commit()
        db.refresh(profile)
        logger.info(f"Enrolled voice profile for Person '{person.full_name}' ({person_id}). Samples: {profile.sample_count}")
        return profile

    def delete_profile(self, db: Session, person_id: str) -> bool:
        """Deletes a voice profile for a person."""
        profile = self.get_profile(db, person_id)
        if not profile:
            return False
        db.delete(profile)
        db.commit()
        logger.info(f"Deleted speaker profile for Person {person_id}")
        return True

    def identify_speaker(
        self,
        db: Session,
        audio_slice: np.ndarray,
        sample_rate: int = SAMPLE_RATE_16K
    ) -> Optional[Tuple[str, float]]:
        """
        Matches an audio slice against all enrolled speaker profiles with active consent.
        Returns: (person_id, similarity_score) if matched, else None.
        """
        profiles = db.query(SpeakerProfile).all()
        if not profiles:
            return None

        slice_feat = self.feature_extractor.extract_features(audio_slice, sample_rate)
        best_match_id = None
        best_score = -1.0

        for prof in profiles:
            # Verify consent is still active
            if not self.has_consent(db, prof.person_id):
                continue

            prof_feat = np.array(json.loads(prof.voice_signature), dtype=np.float32)
            sim = float(np.dot(slice_feat, prof_feat))
            if sim > best_score:
                best_score = sim
                best_match_id = prof.person_id

        if best_match_id and best_score >= self.match_threshold:
            return best_match_id, round(best_score, 4)

        return None


speaker_service = SpeakerService()

