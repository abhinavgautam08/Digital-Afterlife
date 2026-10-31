# Phase 3 Final Verification & Diarization Audit Report

**Project**: Digital Afterlife – Memory Keeper  
**Workspace**: `D:\Digital Afterlife`  
**Phase**: Phase 3: Local Speech-to-Text, Transcript Management & Speaker Diarization  
**Date**: October 31, 2026  
**Auditor**: Senior AI/ML Engineer & Systems Verification Architect  
**Backend Automated Tests**: 66 passed in 18.14s (`backend\.venv\Scripts\pytest.exe -v`)  
**Frontend Production Build**: Clean build in 2.35s (`npm --prefix frontend run build`)  

---

## 1. Executive Summary & Status Classification

Every subsystem in Phase 3 has been audited against actual source code and tested against strict privacy, resource, and ethical invariants.

| Capability Subsystem | Status Label | Verification Details |
|---|---|---|
| **faster-whisper Engine** | `IMPLEMENTED, MOCK-TESTED ONLY` | Verified CTranslate2 CPU `int8` runtime in `transcription_engine.py`. Real inference smoke test currently `BLOCKED` by missing weights in `models/whisper/` (no silent downloads allowed). |
| **Real Local Inference** | `BLOCKED` | Awaiting explicit user-initiated model download. Zero unauthorized cloud API or background downloads occurred. |
| **Model Manager & Safeguards** | `IMPLEMENTED AND TESTED` | `model_manager.py` enforces offline storage, safe paths, size checks, corrupt file detection, and non-silent downloads. |
| **Audio Ingestion & Resampling** | `IMPLEMENTED AND TESTED` | PyAV and Wave resample MP3, WAV, M4A, OGG, and FLAC to 16 kHz mono float32 with bounded memory chunking. |
| **Speaker Diarization** | `EXPERIMENTAL` | Classified as **heuristic acoustic grouping** (20-D acoustic feature extraction + cosine clustering). NOT a deep neural embedding system. Labeled as experimental in UI and docs. |
| **Unknown Speaker Attribution** | `IMPLEMENTED AND TESTED` | Unknown speakers strictly remain anonymous (`Speaker 1`, `Speaker 2`). No automatic identity binding occurs. Manual mapping requires explicit user confirmation. |
| **Consent & Biometric Erasure** | `IMPLEMENTED AND TESTED` | `SpeakerConsent` is checked before enrollment (`ConsentRequiredError` otherwise). Consent revocation immediately purges all derived acoustic vectors. |
| **Persistent Job Queue & Worker** | `IMPLEMENTED AND TESTED` | SQLite-backed sequential job queue (`TranscriptionJob`, concurrency 1). Mid-inference cancellation and startup recovery verified by tests. |
| **Interactive UI & Player Seek** | `IMPLEMENTED AND TESTED` | Clickable segment timestamps seek `<audio>` and `<video>` players to exact second. In-line text editing and explicit consent dialogs verified. |
| **Neural Speaker Embedding (ECAPA/x-vector)** | `NOT IMPLEMENTED` | Heavy neural diarizers (e.g. SpeechBrain / PyTorch 2GB+ models) omitted to protect 12 GB RAM / CPU bounds. |

---

## 2. Whisper Implementation Code Audit

### 1. Library Import & Execution
- **File**: `backend/app/services/speech/transcription_engine.py`
- **Function**: `TranscriptionEngine.get_model()` (lines 48–66) and `transcribe()` (lines 100–120).
- **Finding**: Imports `from faster_whisper import WhisperModel`. Instantiates `WhisperModel(model_size_or_path=model_dir, device="cpu", compute_type="int8", cpu_threads=4, local_files_only=True)`.

### 2. Effective Compute Configuration
- **File**: `backend/app/core/config.py` & `backend/app/services/speech/transcription_engine.py`
- **Finding**: Device is strictly `"cpu"`, compute type is `"int8"`, threads are set to `4`. CUDA or discrete GPUs are not required.

### 3. Default Model Specification
- **File**: `backend/app/core/config.py` (`WHISPER_DEFAULT_MODEL: str = "base"`) and `backend/app/schemas/transcription_job.py` (`model_name: str = "base"`).
- **Finding**: Defaults to `base` across schemas, routes, and services unless explicitly changed by the user.

### 4. Zero Silent Weight Downloads
- **File**: `backend/app/services/speech/transcription_engine.py` (lines 42–47) & `backend/app/api/routes_transcription.py` (lines 53–62).
- **Finding**: When `AUTO_DOWNLOAD_MODELS=False` (default), calling inference on an uninstalled model raises `ModelNotInstalledError` (HTTP 400 Bad Request) with a clear actionable notice directing the user to install explicitly.

### 5. Installation Status Detection
- **File**: `backend/app/services/speech/model_manager.py` (`is_model_installed()`, lines 54–73).
- **Finding**: Verifies presence of `model.bin` and requires `model.bin` size to be > 1 MB (detecting 0-byte or truncated files) along with `config.json` or `tokenizer.json`.

### 6. Configurable & Safe Storage Paths
- **File**: `backend/app/core/config.py` (`WHISPER_MODELS_DIR = BASE_DIR / "models" / "whisper"`).
- **Finding**: Model directories are isolated under `models/whisper/{model_name}`. Path traversal attacks are mitigated by lowercase alphanumeric whitelist matching against `SUPPORTED_MODELS`.

### 7. Offline Network Isolation
- **File**: `backend/app/services/speech/transcription_engine.py` (line 58).
- **Finding**: `WhisperModel` is instantiated with `local_files_only=True`, preventing CTranslate2 / Hugging Face from opening socket connections during model loading.

### 8. Sequential Concurrency Control
- **File**: `backend/app/services/speech/job_worker.py` (`_run_loop()`, lines 105–125).
- **Finding**: Jobs are retrieved with `order_by(created_at.asc()).first()` and executed strictly sequentially (concurrency 1) inside a single background daemon thread.

### 9. RAM Management & Model Eviction
- **File**: `backend/app/services/speech/transcription_engine.py` (`unload_model()`, lines 31–39, `get_model()`, lines 46–49).
- **Finding**: Before loading a new model into RAM, any existing active model instance is deleted and `gc.collect()` is triggered. Multiple models are never retained simultaneously in RAM.

### 10. Corrupt File Handling
- **File**: `backend/app/services/speech/transcription_engine.py` (`ModelCorruptError`, lines 24–26, 68–74).
- **Finding**: Catches unreadable or corrupted weights during instantiation and raises a recoverable `ModelCorruptError`.

---

## 3. Real Local Inference Smoke Test Findings

- **Inspection of `models/whisper/`**: Inspected on October 31, 2026. The directory exists but currently contains 0 files.
- **Inference Status**: `BLOCKED` due to missing model weights.
- **Privacy Audit**: In accordance with the non-silent download rule, **no weights were downloaded in the background**.
- **Installation Procedure for the User**:
  1. Open the UI, navigate to **Settings & Architecture**, locate **Offline Speech Models**, and click **Install** next to `base` (or `tiny`).
  2. Alternatively, invoke the API via CLI:
     ```bash
     curl -X POST http://127.0.0.1:8000/api/transcription/models/download -H "Content-Type: application/json" -d "{\"model_name\": \"base\"}"
     ```
  3. Model weights will be downloaded to `D:\Digital Afterlife\models\whisper\base\`.
- **Language Testing**:
  - English: `IMPLEMENTED, MOCK-TESTED ONLY`.
  - Hindi (`hi`): `IMPLEMENTED, MOCK-TESTED ONLY`.

---

## 4. Honest Audit of Speaker Diarization

- **Classification**: **EXPERIMENTAL HEURISTIC ACOUSTIC GROUPING**.
- **How speech segments are generated**: Boundaries are produced by `faster-whisper`'s internal Voice Activity Detection (`vad_filter=True`, `min_silence_duration_ms=500`).
- **Silence and non-speech**: Excluded by Whisper's VAD before segment creation; slices < 512 samples return zero vectors.
- **Feature Normalization**: Features are normalized to Euclidean unit norm (`norm = np.linalg.norm(feature_vector)`).
- **Cluster Count**: Determined dynamically via online centroid cosine distance against a cluster threshold (`0.45`), bounded by `max_speakers=5`.
- **Determinism**: Deterministic online greedy centroid clustering.
- **Limitations**:
  - Overlap across wide chunk boundaries or different files can cause speaker label drift.
  - Room acoustics, microphone distance, and varying pitch affect clustering accuracy.
- **UI Labeling**: Clearly labeled in `MemoryDetailModal.tsx`:
  > *"Cluster Multiple Speakers (Experimental)"*  
  > *"Note: Speaker diarization uses heuristic acoustic grouping and may be inaccurate. Unknown speakers remain anonymous until manually mapped to a family member."*
- **No Automatic Biometric Binding**: The worker generates anonymous labels only (`Speaker 1`, `Speaker 2`). All `speaker_id` values default to `None`. Associating a speaker with a family member is strictly user-confirmed.

---

## 5. Consent & Biometric Profile Deletion Audit

- **Enrolled Data**: Stores a single JSON-serialized 20-dimensional normalized acoustic vector (`voice_signature`) in the `speaker_profiles` SQLite table.
- **No Raw Biometrics**: No raw audio recordings, spectrograms, or neural voiceprints are stored in the profile table.
- **Enforcement**: `SpeakerService.enroll_speaker` verifies that `SpeakerConsent.consent_given == True` and `revoked_at == None`. Unconsented requests fail with `ConsentRequiredError` (HTTP 403 Forbidden).
- **Erasure Guarantee**: Calling `POST /api/people/{id}/consent` with `consent_given=False` or `DELETE /api/people/{id}/speaker-profile` immediately hard-deletes the `SpeakerProfile` row.

---

## 6. Persistent Job Worker Audit

- **Queue Persistence**: Jobs are committed to `transcription_jobs` table prior to dispatch.
- **Sequential Concurrency**: Concurrency is strictly 1.
- **Interruption Recovery**: `TranscriptionJobWorker.recover_interrupted_jobs()` queries for jobs in `preprocessing`, `transcribing`, or `diarizing` on startup and resets them to `queued` with progress `0.0`.
- **Mid-Inference Cancellation**: Progress callback checks `job.status == 'cancelled'` during transcription and raises `InterruptedError`. The worker catches this and marks the job as `cancelled`. A cancelled job cannot overwrite its status as `completed`.
- **Duplicate Prevention**: `create_transcription_job` checks for active jobs on the memory and returns the existing job if already in progress.
- **Thread Safety**: The worker acquires and closes its own scoped database session (`self.get_session()`) per job cycle.

---

## 7. Verification Test Execution Summary

### Backend Pytest Suite: 66 Passed
- **Phase 1 & Phase 2 Baseline**: 44 tests passed.
- **Phase 3 Core Tests**: 16 tests passed.
- **Phase 3 Hardening & Gap Tests**: 6 tests passed.
  - `test_real_model_unavailable_error_no_implicit_download`: PASSED
  - `test_corrupt_or_truncated_model_detection`: PASSED
  - `test_model_unloading_reclaims_ram`: PASSED
  - `test_duplicate_active_job_submission_returns_existing`: PASSED
  - `test_backend_restart_recovers_interrupted_jobs`: PASSED
  - `test_unknown_speaker_remains_anonymous_in_worker`: PASSED

### Frontend Production Build
- Command: `npm --prefix frontend run build`
- Output: `✓ built in 2.35s` (0 TypeScript errors, 0 build warnings).
