"""
Comprehensive Unit & Integration Test Suite for Phase 3:
Local Speech-to-Text, Diarization, Transcript Management, and Speaker Consent.
"""
import io
import json
import math
import wave
from pathlib import Path
from unittest.mock import patch, MagicMock
import numpy as np
import pytest
from fastapi.testclient import TestClient

from backend.app.core.config import settings
from backend.app.models.memory import Memory
from backend.app.models.person import Person
from backend.app.models.transcript import Transcript, TranscriptSegment
from backend.app.models.transcription_job import TranscriptionJob
from backend.app.models.speaker import SpeakerConsent, SpeakerProfile
from backend.app.services.speech.model_manager import model_manager, SUPPORTED_MODELS
from backend.app.services.speech.audio_converter import audio_converter, SAMPLE_RATE_16K
from backend.app.services.speech.diarization_engine import (
    diarization_engine,
    AcousticFeatureExtractor,
)
from backend.app.services.speech.speaker_service import (
    speaker_service,
    ConsentRequiredError,
)
from backend.app.services.speech.transcription_engine import (
    transcription_engine,
    ModelNotInstalledError,
)
from backend.app.services.speech.job_worker import transcription_worker


def generate_test_wav_bytes(duration_sec: float = 2.0, freq_hz: float = 440.0) -> bytes:
    """Generates synthetic 16 kHz 16-bit mono sine wave PCM bytes."""
    num_samples = int(duration_sec * SAMPLE_RATE_16K)
    t = np.linspace(0, duration_sec, num_samples, endpoint=False)
    waveform = (np.sin(2 * np.pi * freq_hz * t) * 32767.0).astype(np.int16)

    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE_16K)
        wf.writeframes(waveform.tobytes())
    return buffer.getvalue()


# =========================================================================
# 1. Model Manager Tests
# =========================================================================

def test_model_manager_lists_supported_models(tmp_path):
    mgr = model_manager
    models = mgr.list_models()
    names = [m["name"] for m in models]
    assert "tiny" in names
    assert "base" in names
    assert "small" in names

    base_info = next(m for m in models if m["name"] == "base")
    assert base_info["recommended"] is True
    assert base_info["disk_size_mb"] == 145


def test_model_manager_offline_detection(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "WHISPER_MODELS_DIR", tmp_path)
    from backend.app.services.speech.model_manager import ModelManager

    mgr = ModelManager(models_dir=tmp_path)
    assert not mgr.is_model_installed("base")

    # Simulate installed model files
    base_dir = tmp_path / "base"
    base_dir.mkdir(parents=True, exist_ok=True)
    (base_dir / "model.bin").write_bytes(b"x" * (1024 * 1024 + 1))
    (base_dir / "config.json").write_text("{}")

    assert mgr.is_model_installed("base")
    assert mgr.get_model_size_on_disk("base") > 0


def test_model_manager_rejects_invalid_model_download():
    with pytest.raises(ValueError, match="Unsupported model"):
        model_manager.download_model("invalid_model_xyz")


# =========================================================================
# 2. Audio Preprocessing & Chunking Tests
# =========================================================================

def test_audio_converter_loads_wav_float32():
    wav_bytes = generate_test_wav_bytes(duration_sec=1.5, freq_hz=300.0)
    audio_data, duration = audio_converter.load_audio_as_float32(wav_bytes)

    assert isinstance(audio_data, np.ndarray)
    assert audio_data.dtype == np.float32
    assert abs(duration - 1.5) < 0.05
    assert len(audio_data) == int(1.5 * SAMPLE_RATE_16K)
    # Check bounded normalization
    assert np.max(audio_data) <= 1.0
    assert np.min(audio_data) >= -1.0


def test_audio_converter_repacks_wav_bytes():
    wav_bytes = generate_test_wav_bytes(duration_sec=1.0)
    audio_data, _ = audio_converter.load_audio_as_float32(wav_bytes)
    output_bytes = audio_converter.convert_to_wav_bytes(audio_data)

    assert output_bytes[:4] == b"RIFF"
    assert output_bytes[8:12] == b"WAVE"


def test_audio_converter_chunking_with_overlap():
    total_sec = 65.0  # 65 seconds audio
    samples = np.zeros(int(total_sec * SAMPLE_RATE_16K), dtype=np.float32)

    chunks = list(audio_converter.chunk_audio(samples, chunk_duration_sec=30.0, overlap_sec=2.0))
    # 0..30s, 28..58s, 56..65s => 3 chunks
    assert len(chunks) == 3
    assert chunks[0][0] == 0
    assert chunks[0][1] == 0.0
    assert chunks[0][2] == 30.0
    assert chunks[1][1] == 28.0


# =========================================================================
# 3. Acoustic Biometrics & Diarization Tests
# =========================================================================

def test_acoustic_feature_extractor():
    extractor = AcousticFeatureExtractor()
    audio = np.random.uniform(-0.5, 0.5, 16000).astype(np.float32)
    feat = extractor.extract_features(audio)

    assert isinstance(feat, np.ndarray)
    assert len(feat) == 20
    # Unit norm verification
    norm = np.linalg.norm(feat)
    assert abs(norm - 1.0) < 1e-4


def test_diarization_engine_assigns_speakers():
    # Construct two distinct synthetic speakers (one low freq 200 Hz, one high freq 800 Hz)
    dur = 2.0
    t = np.linspace(0, dur, int(dur * SAMPLE_RATE_16K), endpoint=False)
    speaker_a = (np.sin(2 * np.pi * 200 * t) * 0.8).astype(np.float32)
    speaker_b = (np.sin(2 * np.pi * 800 * t) * 0.8).astype(np.float32)
    combined_audio = np.concatenate([speaker_a, speaker_b])

    segments = [
        {"start": 0.0, "end": 2.0, "text": "Hello from speaker A"},
        {"start": 2.0, "end": 4.0, "text": "Greetings from speaker B"},
    ]

    diarized = diarization_engine.diarize_segments(combined_audio, segments)
    assert len(diarized) == 2
    assert "speaker_label" in diarized[0]
    assert "speaker_label" in diarized[1]
    # Distinct frequencies should yield distinct clusters
    assert diarized[0]["speaker_label"] != diarized[1]["speaker_label"]


def test_diarization_single_segment_fallback():
    audio = np.zeros(16000, dtype=np.float32)
    segments = [{"start": 0.0, "end": 1.0, "text": "Single segment sentence"}]
    diarized = diarization_engine.diarize_segments(audio, segments)
    assert len(diarized) == 1
    assert diarized[0]["speaker_label"] == "Speaker 1"


# =========================================================================
# 4. Consent-Based Speaker Profile Tests
# =========================================================================

def test_speaker_enrollment_strictly_enforces_consent(test_db):
    person = Person(full_name="Grandfather Anand", relationship="Grandfather")
    test_db.add(person)
    test_db.commit()

    sample_audio = np.random.uniform(-0.4, 0.4, 16000).astype(np.float32)

    # Enrollment without prior consent MUST raise ConsentRequiredError
    with pytest.raises(ConsentRequiredError, match="explicit consent has not been granted"):
        speaker_service.enroll_speaker(test_db, person.id, sample_audio)

    # Grant explicit consent
    consent = speaker_service.record_consent(
        test_db,
        person_id=person.id,
        consent_given=True,
        consent_notes="Oral history interview consent signed"
    )
    assert consent.consent_given is True
    assert speaker_service.has_consent(test_db, person.id) is True

    # Now enrollment succeeds
    profile = speaker_service.enroll_speaker(test_db, person.id, sample_audio)
    assert profile.person_id == person.id
    assert profile.sample_count == 1
    assert len(json.loads(profile.voice_signature)) == 20

    # Revoking consent MUST purge the voice profile
    revoked = speaker_service.revoke_consent(test_db, person.id)
    assert revoked is True
    assert speaker_service.has_consent(test_db, person.id) is False
    assert speaker_service.get_profile(test_db, person.id) is None


# =========================================================================
# 5. REST API & Background Job Integration Tests
# =========================================================================

def test_api_transcription_models_and_status(client: TestClient):
    # Models endpoint
    res = client.get("/api/transcription/models")
    assert res.status_code == 200
    models = res.json()
    assert len(models) >= 3
    assert any(m["name"] == "base" for m in models)

    # Status endpoint
    status_res = client.get("/api/transcription/status")
    assert status_res.status_code == 200
    status_data = status_res.json()
    assert status_data["device"] == "cpu"
    assert status_data["compute_type"] == "int8"
    assert status_data["queue_concurrency"] == 1
    assert status_data["pyav_available"] is True


def test_api_submit_transcription_validation(client: TestClient, test_db):
    # 1. Non-existent memory => 404
    bad_res = client.post("/api/memories/non-existent-uuid/transcription", json={"model_name": "base"})
    assert bad_res.status_code == 404

    # 2. Non-audio/video memory (e.g. story / document) => 400
    doc_mem = Memory(
        title="Family Letter",
        memory_type="document",
        original_filename="letter.txt",
        stored_filename="letter.txt",
        mime_type="text/plain",
        file_size=120,
        file_path="dummy/path",
        processing_status="completed"
    )
    test_db.add(doc_mem)
    test_db.commit()

    type_res = client.post(f"/api/memories/{doc_mem.id}/transcription", json={"model_name": "base"})
    assert type_res.status_code == 400
    assert "cannot be transcribed" in type_res.json()["detail"]


def test_api_transcription_uninstalled_model_guard(client: TestClient, test_db, monkeypatch):
    # Create audio memory
    audio_mem = Memory(
        title="Oral Ancestry Tape",
        memory_type="audio",
        original_filename="tape.wav",
        stored_filename="tape.wav",
        mime_type="audio/wav",
        file_size=5000,
        file_path="dummy/tape.wav",
        processing_status="completed"
    )
    test_db.add(audio_mem)
    test_db.commit()

    # Mock model as uninstalled and auto-download disabled
    monkeypatch.setattr(model_manager, "is_model_installed", lambda name: False)
    monkeypatch.setattr(settings, "AUTO_DOWNLOAD_MODELS", False)

    res = client.post(
        f"/api/memories/{audio_mem.id}/transcription",
        json={"model_name": "base"}
    )
    assert res.status_code == 400
    assert "not installed locally" in res.json()["detail"]


def test_api_transcription_job_lifecycle_and_execution(client: TestClient, test_db, tmp_path, monkeypatch):
    # Save a valid synthetic WAV file
    wav_path = tmp_path / "voice.wav"
    wav_path.write_bytes(generate_test_wav_bytes(duration_sec=2.0))

    audio_mem = Memory(
        title="Family Gathering Audio",
        memory_type="audio",
        original_filename="voice.wav",
        stored_filename="voice.wav",
        mime_type="audio/wav",
        file_size=len(wav_path.read_bytes()),
        file_path=str(wav_path),
        processing_status="completed"
    )
    test_db.add(audio_mem)
    test_db.commit()

    # Mock model as installed
    monkeypatch.setattr(model_manager, "is_model_installed", lambda name: True)

    from sqlalchemy.orm import sessionmaker
    test_sessionmaker = sessionmaker(autocommit=False, autoflush=False, bind=test_db.get_bind())
    monkeypatch.setattr(transcription_worker, "get_session", test_sessionmaker)

    # Mock transcription engine transcribe output
    mock_transcription_result = {
        "full_text": "We built this family house in nineteen sixty two.",
        "detected_language": "en",
        "language_probability": 0.98,
        "segments": [
            {
                "start": 0.0,
                "end": 2.0,
                "text": "We built this family house in nineteen sixty two.",
                "confidence": 0.95
            }
        ],
        "audio_duration": 2.0,
        "processing_duration": 0.42,
        "audio_data": np.zeros(32000, dtype=np.float32)
    }

    monkeypatch.setattr(transcription_engine, "transcribe", lambda *args, **kwargs: mock_transcription_result)
    monkeypatch.setattr(transcription_worker, "notify", lambda: None)

    # 1. Enqueue Job
    res = client.post(
        f"/api/memories/{audio_mem.id}/transcription",
        json={"model_name": "base", "language": "en", "enable_diarization": True}
    )
    assert res.status_code == 202
    job_data = res.json()
    job_id = job_data["id"]
    assert job_data["status"] == "queued"
    assert job_data["model_name"] == "base"

    # 2. List Jobs
    list_res = client.get("/api/transcription/jobs")
    assert list_res.status_code == 200
    assert any(j["id"] == job_id for j in list_res.json())

    # 3. Process job synchronously via worker
    processed = transcription_worker._process_next_job()
    assert processed is True

    # 4. Check Job Status is now completed
    job_check = client.get(f"/api/transcription/jobs/{job_id}")
    assert job_check.status_code == 200
    assert job_check.json()["status"] == "completed"
    assert job_check.json()["progress"] == 100.0

    # 5. Fetch Generated Transcript
    tr_res = client.get(f"/api/memories/{audio_mem.id}/transcript")
    assert tr_res.status_code == 200
    tr_data = tr_res.json()
    assert tr_data["transcript_text"] == "We built this family house in nineteen sixty two."
    assert tr_data["detected_language"] == "en"
    assert len(tr_data["segments"]) == 1

    segment = tr_data["segments"][0]
    assert segment["speaker_label"] == "Speaker 1"
    assert segment["start_time"] == 0.0
    assert segment["end_time"] == 2.0

    # 6. Edit Transcript Segment (PATCH)
    transcript_id = tr_data["id"]
    patch_res = client.patch(
        f"/api/transcripts/{transcript_id}",
        json={
            "transcript_text": "We built this historic family house in 1962.",
            "segments": [
                {
                    "id": segment["id"],
                    "text": "We built this historic family house in 1962.",
                    "speaker_label": "Grandfather"
                }
            ]
        }
    )
    assert patch_res.status_code == 200
    patched_data = patch_res.json()
    assert patched_data["transcript_text"] == "We built this historic family house in 1962."
    assert patched_data["segments"][0]["text"] == "We built this historic family house in 1962."
    assert patched_data["segments"][0]["speaker_label"] == "Grandfather"

    # 7. Delete Transcript
    del_res = client.delete(f"/api/transcripts/{transcript_id}")
    assert del_res.status_code == 200
    assert del_res.json()["success"] is True

    # Confirm 404 after deletion
    assert client.get(f"/api/memories/{audio_mem.id}/transcript").status_code == 404


def test_api_cancel_transcription_job(client: TestClient, test_db):
    audio_mem = Memory(
        title="Long Story Audio",
        memory_type="audio",
        original_filename="story.wav",
        stored_filename="story.wav",
        mime_type="audio/wav",
        file_size=1000,
        file_path="dummy/story.wav",
        processing_status="completed"
    )
    test_db.add(audio_mem)
    test_db.commit()

    job = TranscriptionJob(
        memory_id=audio_mem.id,
        status="queued",
        progress=0.0,
        current_stage="Queued",
        model_name="base"
    )
    test_db.add(job)
    test_db.commit()

    cancel_res = client.post(f"/api/transcription/jobs/{job.id}/cancel")
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == "cancelled"


def test_api_speaker_consent_and_profile_routes(client: TestClient, test_db, tmp_path):
    person = Person(full_name="Mother Shanti", relationship="Mother")
    test_db.add(person)
    test_db.commit()

    # Initial consent is None
    consent_res = client.get(f"/api/people/{person.id}/consent")
    assert consent_res.status_code == 200
    assert consent_res.json() is None

    # Try enrolling profile without consent => 403 Forbidden
    enroll_bad = client.post(
        f"/api/people/{person.id}/speaker-profile/enroll",
        json={"memory_id": "dummy-id"}
    )
    assert enroll_bad.status_code == 403

    # Record consent
    record_res = client.post(
        f"/api/people/{person.id}/consent",
        json={"consent_given": True, "consent_notes": "Mother gave consent for oral preservation."}
    )
    assert record_res.status_code == 200
    assert record_res.json()["consent_given"] is True

    # Verify consent is retrieved
    check_consent = client.get(f"/api/people/{person.id}/consent")
    assert check_consent.status_code == 200
    assert check_consent.json()["consent_given"] is True

    # Prepare audio memory for enrollment
    wav_path = tmp_path / "shanti_voice.wav"
    wav_path.write_bytes(generate_test_wav_bytes(duration_sec=1.5))
    audio_mem = Memory(
        title="Mother Interview",
        memory_type="audio",
        original_filename="shanti.wav",
        stored_filename="shanti.wav",
        mime_type="audio/wav",
        file_size=len(wav_path.read_bytes()),
        file_path=str(wav_path),
        processing_status="completed"
    )
    test_db.add(audio_mem)
    test_db.commit()

    # Enroll profile with consent => 201 Created
    enroll_res = client.post(
        f"/api/people/{person.id}/speaker-profile/enroll",
        json={"memory_id": audio_mem.id, "start_time": 0.0, "end_time": 1.5}
    )
    assert enroll_res.status_code == 201
    assert enroll_res.json()["person_id"] == person.id
    assert enroll_res.json()["sample_count"] == 1

    # Fetch profile
    prof_res = client.get(f"/api/people/{person.id}/speaker-profile")
    assert prof_res.status_code == 200
    assert prof_res.json()["sample_count"] == 1

    # Delete profile
    del_prof = client.delete(f"/api/people/{person.id}/speaker-profile")
    assert del_prof.status_code == 200
    assert del_prof.json()["success"] is True

    # Verify profile deleted
    assert client.get(f"/api/people/{person.id}/speaker-profile").json() is None


# =========================================================================
# 6. Focused Gap Verification Tests (Audit Requirements)
# =========================================================================

def test_real_model_unavailable_error_no_implicit_download(monkeypatch):
    """Verifies that an uninstalled model produces clear error and does NOT silently download."""
    monkeypatch.setattr(settings, "AUTO_DOWNLOAD_MODELS", False)
    monkeypatch.setattr(model_manager, "is_model_installed", lambda name: False)

    download_called = False
    def fake_download(*args, **kwargs):
        nonlocal download_called
        download_called = True
        return Path("dummy")

    monkeypatch.setattr(model_manager, "download_model", fake_download)

    from backend.app.services.speech.transcription_engine import ModelNotInstalledError
    with pytest.raises(ModelNotInstalledError, match="is not installed locally"):
        transcription_engine.get_model("small")

    assert download_called is False


def test_corrupt_or_truncated_model_detection(tmp_path, monkeypatch):
    """Verifies that 0-byte or truncated model files are detected as corrupt/uninstalled."""
    monkeypatch.setattr(settings, "WHISPER_MODELS_DIR", tmp_path)
    from backend.app.services.speech.model_manager import ModelManager

    mgr = ModelManager(models_dir=tmp_path)
    base_dir = tmp_path / "base"
    base_dir.mkdir(parents=True, exist_ok=True)
    # Truncated 10-byte model file
    (base_dir / "model.bin").write_bytes(b"truncated!")
    (base_dir / "config.json").write_text("{}")

    assert mgr.is_model_installed("base") is False


def test_model_unloading_reclaims_ram():
    """Verifies that unload_model frees the cached model reference."""
    transcription_engine._current_model = "mock_model"
    transcription_engine._current_model_name = "base"

    transcription_engine.unload_model()
    assert transcription_engine._current_model is None
    assert transcription_engine._current_model_name is None


def test_duplicate_active_job_submission_returns_existing(client: TestClient, test_db, monkeypatch):
    """Verifies that submitting a transcription job for an already-active job returns the existing job."""
    audio_mem = Memory(
        title="Oral Interview Dup Test",
        memory_type="audio",
        original_filename="interview.wav",
        stored_filename="interview.wav",
        mime_type="audio/wav",
        file_size=2000,
        file_path="dummy/interview.wav",
        processing_status="completed"
    )
    test_db.add(audio_mem)
    test_db.commit()

    monkeypatch.setattr(model_manager, "is_model_installed", lambda name: True)
    monkeypatch.setattr(transcription_worker, "notify", lambda: None)

    res1 = client.post(f"/api/memories/{audio_mem.id}/transcription", json={"model_name": "base"})
    assert res1.status_code == 202
    job1_id = res1.json()["id"]

    # Submit second job while first is still queued
    res2 = client.post(f"/api/memories/{audio_mem.id}/transcription", json={"model_name": "base"})
    assert res2.status_code == 202
    job2_id = res2.json()["id"]

    assert job1_id == job2_id


def test_backend_restart_recovers_interrupted_jobs(test_db, monkeypatch):
    """Verifies that worker recovers jobs stuck in preprocessing/transcribing/diarizing states."""
    from sqlalchemy.orm import sessionmaker
    test_sessionmaker = sessionmaker(autocommit=False, autoflush=False, bind=test_db.get_bind())
    monkeypatch.setattr(transcription_worker, "get_session", test_sessionmaker)

    mem = Memory(
        title="Recovery Test Memory",
        memory_type="audio",
        original_filename="rec.wav",
        stored_filename="rec.wav",
        file_path="dummy/rec.wav",
        mime_type="audio/wav",
        file_size=100,
        processing_status="completed"
    )
    test_db.add(mem)
    test_db.commit()

    stuck_job = TranscriptionJob(
        memory_id=mem.id,
        status="transcribing",
        progress=45.0,
        current_stage="Transcribing speech to text",
        model_name="base"
    )
    test_db.add(stuck_job)
    test_db.commit()

    transcription_worker.recover_interrupted_jobs()

    test_db.refresh(stuck_job)
    assert stuck_job.status == "queued"
    assert "recovered after restart" in stuck_job.current_stage
    assert stuck_job.progress == 0.0


def test_unknown_speaker_remains_anonymous_in_worker(client: TestClient, test_db, tmp_path, monkeypatch):
    """
    Verifies that during background processing, speaker segments are NEVER automatically
    associated with family members. They remain anonymous until user confirms in the UI.
    """
    # Create person with consented profile
    person = Person(full_name="Grandfather Prem", relationship="Grandfather")
    test_db.add(person)
    test_db.commit()

    consent = SpeakerConsent(person_id=person.id, consent_given=True, consent_date=test_db.query(Person).first().created_at)
    test_db.add(consent)
    profile = SpeakerProfile(person_id=person.id, voice_signature=json.dumps([0.1]*20), sample_count=1)
    test_db.add(profile)
    test_db.commit()

    wav_path = tmp_path / "prem.wav"
    wav_path.write_bytes(generate_test_wav_bytes(duration_sec=2.0))
    audio_mem = Memory(
        title="Prem Memory",
        memory_type="audio",
        original_filename="prem.wav",
        stored_filename="prem.wav",
        mime_type="audio/wav",
        file_size=len(wav_path.read_bytes()),
        file_path=str(wav_path),
        processing_status="completed"
    )
    test_db.add(audio_mem)
    test_db.commit()

    monkeypatch.setattr(model_manager, "is_model_installed", lambda name: True)
    from sqlalchemy.orm import sessionmaker
    test_sessionmaker = sessionmaker(autocommit=False, autoflush=False, bind=test_db.get_bind())
    monkeypatch.setattr(transcription_worker, "get_session", test_sessionmaker)

    mock_result = {
        "full_text": "Story from the village.",
        "detected_language": "en",
        "language_probability": 0.99,
        "segments": [{"start": 0.0, "end": 2.0, "text": "Story from the village.", "confidence": 0.9}],
        "audio_duration": 2.0,
        "processing_duration": 0.3,
        "audio_data": np.zeros(32000, dtype=np.float32)
    }
    monkeypatch.setattr(transcription_engine, "transcribe", lambda *args, **kwargs: mock_result)
    monkeypatch.setattr(transcription_worker, "notify", lambda: None)

    client.post(f"/api/memories/{audio_mem.id}/transcription", json={"model_name": "base"})
    transcription_worker._process_next_job()

    tr_res = client.get(f"/api/memories/{audio_mem.id}/transcript")
    assert tr_res.status_code == 200
    seg = tr_res.json()["segments"][0]
    # Critical Privacy Check: speaker_id MUST be None (no automatic binding)
    assert seg["speaker_id"] is None
    assert seg["speaker_label"] == "Speaker 1"

