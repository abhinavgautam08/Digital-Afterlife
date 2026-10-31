# Digital Afterlife — Memory Keeper

> *"Your memories. Your machine. Your legacy."*

Digital Afterlife is an offline-first, privacy-focused sovereign memory vault engineered to preserve family histories, photographs, voice recordings, oral histories, personal videos, documents, and family stories. Operating entirely on local hardware with open-weight AI, your family heritage remains sovereign, private, and permanent—never uploaded to commercial clouds or used to train third-party models.

---

## Core Capabilities & Architecture

### 1. Multimedia Memory Vault (Phase 2)
- **Supported Formats (17 Distinct Extensions across 5 Categories)**:
  - **Photographs**: JPG, JPEG, PNG, WEBP, GIF.
  - **Audio & Oral Histories**: MP3, WAV, M4A, OGG, FLAC.
  - **Personal Videos**: MP4, WEBM, MOV.
  - **Historical Documents & Letters**: PDF, TXT, MD, DOCX.
  - **Written Stories**: Narrative personal memoirs and reflections.
- **Deep Content Validation**:
  - Magic byte header inspection independent of browser-supplied MIME types.
  - Rejection of executables (`.exe`, ELF, Mach-O, shell scripts), scripts, HTML, and malformed files.
  - 100 MB per-file upload threshold with streaming enforcement.
  - SHA-256 cryptographic duplicate detection (`409 Conflict`).
- **Ingestion & Metadata Pipeline**:
  - **Image Processing**: Safe EXIF parsing (GPS coordinates stripped for family privacy, capture dates preserved), dimensions (`width × height`), orientation transposition, decompression-bomb guards, and automated 480×480 JPEG thumbnail generation.
  - **Audio Processing**: Duration calculation and audio metadata extraction via `mutagen` and standard wave parsers.
  - **Video Processing**: Pure-Python MP4/MOV container atom parsing and WebM EBML element parsing for duration and dimensions without external FFmpeg dependencies.
  - **Document Processing**: Complete text extraction for PDFs (`pypdf`), Word documents (`python-docx`), and plain text/Markdown files (`utf-8`), bounded to 150,000 characters and indexed for search.

### 2. Organization & Discovery
- **Rich Memory Filtering**:
  - Filter by Category (Photographs, Audio, Video, Documents, Stories).
  - Filter by Connected Family Member (`person_id`).
  - Filter by Theme Tag (`tag`).
  - Filter by Date Range (`date_from`, `date_to`).
  - Multi-attribute text search matching title, narrative notes, location, and extracted document text (`/api/memories/search`).
  - Sorting: Newest Ingested, Oldest Ingested, Event Date (Newest/Oldest), Title (A-Z), and File Size.
- **Full Tag Management (`/api/tags`)**:
  - CRUD operations on tags (`#Childhood`, `#Celebration`, `#Travel`, `#Letters`, `#Recipe`, `#FamilyTradition`).
  - Association counts tracking linked memories.
- **Metadata Editing (`PATCH /api/memories/{id}`)**:
  - Update memory title, description, location, event date, privacy level, tags, and associated people at any time.

### 3. Family & Lineage Directory
- Register family members, ancestors, and loved ones with biographical notes.
- Link memories directly to multiple individuals and view all associated artifacts in a dedicated lineage drawer.

### 4. Local Speech-to-Text & Speaker Diarization (Phase 3)
- **Engine**: `faster-whisper` quantized to `int8` on CPU (`device="cpu"`, `compute_type="int8"`). Multi-threaded execution (`WHISPER_CPU_THREADS=4`), zero discrete GPU requirements.
- **Languages**: English, Hindi (`hi`), and auto-detection with language probability reporting.
- **Audio Preprocessing**: In-process resampling of MP3, WAV, M4A, OGG, and FLAC to 16 kHz mono float32 waveforms using PyAV (`av`) with standard library `wave` fallback.
- **Persistent Background Queue**: Sequential execution (`TranscriptionJob`, concurrency 1) to protect host CPU and 12 GB RAM headroom. Automatic recovery of interrupted jobs across server restarts, and job cancellation support.
- **Interactive Audio Timeline**: Clickable timestamped segments (`[▶ 00:15 - 00:32]`) in `MemoryDetailModal` jump and seek media playback directly.
- **Speaker Diarization**: 20-dimensional normalized acoustic feature clustering assigns anonymous speaker labels (`Speaker 1`, `Speaker 2`) completely offline without external PyTorch/cloud runtimes.
- **Consent-Based Voice Profiles**: Mandatory explicit prior consent (`SpeakerConsent`) before enrolling family voice signatures (`SpeakerProfile`). Revoking consent permanently purges all acoustic biometric vectors.
- **Offline Model Management**: Models (`tiny`, `base`, `small`) stored in `models/whisper/`. Zero automatic or silent downloads; downloads require explicit user trigger.

### 5. Local Semantic Memory Search & RAG (Phase 4)
- **Engine**: ChromaDB local vector storage (`data/vector_store/`) with cosine space.
- **Embeddings**: `intfloat/multilingual-e5-small` (384-D) running locally on CPU via ONNX Runtime (`onnxruntime`) and `tokenizers`.
- **E5 Task Prefixes**: Enforces `passage: ` for indexing and `query: ` for search queries.
- **Chunking Pipeline**: Target 400–600 tokens with 50–80 token overlap. Sentence-preserving heuristics for English and Hindi (`.`, `?`, `!`, `।`). Continuous timestamp preservation for transcript segments.
- **Hybrid Retrieval**: Combines semantic vector proximity with SQLite lexical matching via Reciprocal Rank Fusion (RRF, $k=60$), coupled with source diversification guards to avoid single-document monopolization.
- **Grounded Answer Generation**: Integrates with local Ollama (`qwen2.5:3b`) under strict non-fabrication rules, prompt injection defense, and mandatory abstention on insufficient evidence.
- **Interactive Citations**: Clickable source citations open original photos, documents, and transcripts, automatically seeking the media player to cited timestamps.

### 6. AI Storytelling, Biographies, Timelines & Remembrance Pages (Phase 5)
- **Personal Biographies**: Multi-chapter life histories synthesized strictly from retrieved family memories, documents, and transcripts with cross-referenced evidence tags.
- **Life Timelines**: Chronological reconstruction of milestones, migrations, achievements, and family gatherings with direct memory associations.
- **Remembrance Pages (Digital Ofrenda)**: Dedicated commemorative spaces honoring departed loved ones, featuring treasured memories, personal tributes, favorite songs/foods, and family reflections.
- **Curated Collections**: Thematic groupings of memories (e.g., *Family Recipes*, *Immigration Journey*, *Letters from War*).
- **Ethical Safeguards**: System strictly abstains from inventing unrecorded memories, false dates, fabricated quotes, or hallucinatory relatives.

### 7. Local Vault Encryption, Data Protection & Privacy (Phase 6)
- **Zero-Knowledge Architecture**: No cloud KMS, remote key servers, or telemetry. All keys derived and managed locally.
- **Cryptographic Primitives**:
  - **Authenticated Streaming Encryption**: AES-256-GCM via the `cryptography` library. Media files, documents, and thumbnails encrypted in bounded 64 KB chunks (`DAENC1` format) with per-chunk derived nonces and Associated Authenticated Data (AAD) index binding.
  - **Key Derivation Function (KDF)**: Argon2id (`m=64MB, t=3, p=4, salt=16B`) derives Key Encryption Keys (KEKs) from the master passphrase and emergency recovery key.
  - **Envelope Security (`VaultEnvelope`)**: Cryptographically secure 256-bit Data Encryption Key (DEK) wrapped under Password KEK and Recovery KEK inside `data/security/vault_envelope.json`.
  - **Field-Level Encryption (`FieldCipher`)**: SQLite sensitive text fields (`description`, `extracted_text`, `transcript_text`, `content`, `user_personal_notes`) encrypted using authenticated AES-256-GCM envelopes (`ENC:v1:`).
- **Access Control & Auto-Lock**:
  - In-memory DEK zeroed out upon vault lock or after configurable inactivity timeouts (default 15 minutes).
  - All memory, media, voice, search, RAG, and storytelling API routes reject access with **HTTP 423 Locked** when the vault is locked.
- **Safe Reversible Migration & Unified Backups**:
  - Non-destructive migration verifies SHA-256 integrity of decrypted files against originals before unlinking plaintext data.
  - Full rollback capability cleanly restores plaintext records if needed.
  - Unified encrypted `.da-backup` archive created completely in memory (`io.BytesIO`) encapsulating database, security envelope, and encrypted media with zero temporary plaintext files written to disk.

---

## Known Security, Privacy & Runtime Limitations

1. **ChromaDB Vector Store Plaintext-at-Rest Exposure**:
   - ChromaDB v0.4+ stores raw text chunks in its local SQLite database (`data/vector_store/chroma.sqlite3`).
   - While application-level API endpoints and query methods return HTTP 423 Locked, an attacker with physical or offline access to an unencrypted drive could inspect `chroma.sqlite3`.
   - **Prerequisite:** Users must enable OS-level Full Disk Encryption (**BitLocker** on Windows, **FileVault** on macOS, **LUKS** on Linux).
2. **CPython Runtime Memory Residency**:
   - Although the DEK `bytearray` is explicitly zeroed on lock (`_dek[i] = 0`), CPython's string interning, immutable `bytes` copies, garbage collection cycles, and OS swap files mean user-space memory zeroization cannot mathematically guarantee the absence of memory traces against kernel-level memory dumping.
3. **Local AI Model Availability**:
   - When local embedding weights (`multilingual-e5-small`) or Ollama (`qwen2.5:3b`) are unavailable, the application operates in safe keyword-only fallback mode. The system never fabricates responses or silently uses mock models in production.

---

## Technology Stack

- **Frontend**: React 19, Vite 8, TypeScript, Tailwind CSS, Lucide React
- **Backend**: Python 3.12+, FastAPI, Pydantic, SQLAlchemy 2.0, SQLite (WAL mode)
- **Vector Database**: ChromaDB (Persistent local client)
- **Embedding & STT Runtimes**: ONNX Runtime, Tokenizers, ctranslate2, faster-whisper
- **Cryptography**: `cryptography` (AES-256-GCM), `argon2-cffi` (Argon2id)
- **Multimedia Processing**: Pillow, mutagen, pypdf, python-docx, PyAV
- **Local AI Runtime**: Ollama with Qwen2.5 3B Instruct (Apache 2.0 open-weight)

---

## Installation & Setup

### 1. Workspace
```bash
cd "d:\Digital Afterlife"
```

### 2. Backend Setup
```bash
# Activate virtual environment
# Windows:
backend\.venv\Scripts\activate
# macOS/Linux:
source backend/.venv/bin/activate

# Install requirements
pip install -r backend/requirements.txt

# Initialize database schema
python -c "from backend.app.database.session import init_db; init_db()"
```

### 3. Frontend Setup
```bash
cd frontend
npm install
```

---

## Running the Application

### Option A: Using Convenience Scripts
**Windows**:
- Terminal 1: `scripts\run_backend.bat`
- Terminal 2: `scripts\run_frontend.bat`

**macOS / Linux**:
- Terminal 1: `bash scripts/run_backend.sh`
- Terminal 2: `bash scripts/run_frontend.sh`

### Option B: Running Directly via Command Line
**Start Backend**:
```bash
backend\.venv\Scripts\uvicorn.exe backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```
Interactive OpenAPI documentation is available at `http://127.0.0.1:8000/api/docs`.

**Start Frontend**:
```bash
cd frontend
npm run dev
```
Navigate to **`http://127.0.0.1:5173`**.

---

## Running Automated Tests

Run the complete backend regression test suite (132 automated tests covering all 6 phases: multimedia vault, format matrix, duplicate detection, speech-to-text, diarization, consent security, semantic search, RAG, storytelling, biographies, timelines, encryption, tampering detection, and auto-lock):

```bash
backend\.venv\Scripts\pytest.exe -v
```

Verify frontend TypeScript type-safety and production build:
```bash
cd frontend
npm run build
```

---

## Documentation Directory

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md): Modular system design, ingestion pipeline, speech services, and data flow.
- [`docs/PRIVACY.md`](docs/PRIVACY.md): Core privacy principles, local loopback commitments, biometric consent, and encryption notice.
- [`docs/API.md`](docs/API.md): Complete REST endpoint specifications, query parameters, and payloads.
- [`docs/LOCAL_AI_SETUP.md`](docs/LOCAL_AI_SETUP.md): Setup instructions for Ollama and local model runtimes.
- [`docs/SPEECH_ENGINE.md`](docs/SPEECH_ENGINE.md): Architectural guide for `faster-whisper` STT and diarization.
- [`docs/SPEAKER_CONSENT.md`](docs/SPEAKER_CONSENT.md): Biometric privacy framework and consent protocols.
- [`docs/RAG_ARCHITECTURE.md`](docs/RAG_ARCHITECTURE.md): Local vector store and hybrid RRF retrieval architecture.
- [`docs/PHASE1_REPORT.md`](docs/PHASE1_REPORT.md): Phase 1 Foundation & Architecture report.
- [`docs/PHASE2_REPORT.md`](docs/PHASE2_REPORT.md): Phase 2 Memory Vault report.
- [`docs/PHASE2_FINAL_AUDIT.md`](docs/PHASE2_FINAL_AUDIT.md): Phase 2 Final Hardening Audit report.
- [`docs/PHASE3_REPORT.md`](docs/PHASE3_REPORT.md): Phase 3 Local STT & Diarization engineering report.
- [`docs/PHASE4_REPORT.md`](docs/PHASE4_REPORT.md): Phase 4 Semantic Search & Local RAG report.
- [`docs/PHASE5_REPORT.md`](docs/PHASE5_REPORT.md): Phase 5 AI Storytelling, Timelines & Remembrance Pages report.
- [`docs/PHASE5_INDEPENDENT_AUDIT.md`](docs/PHASE5_INDEPENDENT_AUDIT.md): Phase 5 Independent Quality & Security Audit report.
- [`docs/PHASE6_SECURITY_REPORT.md`](docs/PHASE6_SECURITY_REPORT.md): Phase 6 Encryption Architecture & Key Management report.
- [`docs/PHASE6_FINAL_RELEASE_AUDIT.md`](docs/PHASE6_FINAL_RELEASE_AUDIT.md): Phase 6 Final Release Gate & Verification Audit report.
- [`docs/PHASE8_RELEASE_REPORT.md`](docs/PHASE8_RELEASE_REPORT.md): Phase 8 Final Release Preparation & Verification report.
- [`docs/HACKTOBERFEST_SUBMISSION.md`](docs/HACKTOBERFEST_SUBMISSION.md): Hacktoberfest 2026 Week 4 DEV Challenge Submission draft.
