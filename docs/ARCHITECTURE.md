# Architecture Specification: Digital Afterlife (Phases 1 & 2)

**Application**: Digital Afterlife – Memory Keeper  
**Tagline**: *"Your memories. Your machine. Your legacy."*  
**Phases Completed**: Phase 1: Foundation & Architecture, Phase 2: Memory Vault & Multimedia Preservation  
**Status**: Implemented & Audited  

---

## 1. Architectural Philosophy

Digital Afterlife is architected from first principles as an **offline-first, zero-cloud, multimedia personal heritage preservation system**. The technical choices strictly uphold three axioms:

1. **Memory Sovereignty**: Personal photographs, audio recordings, family letters, and oral histories must reside exclusively on the owner's physical disk.
2. **Local Machine Inference**: No biometric data, private narrative, or audio transcript is ever transmitted over the network or processed by cloud APIs.
3. **Decoupled Desktop-Ready Modularity**: Backend domain logic is decoupled from HTTP transport; UI components communicate over local REST contracts, enabling a seamless transition into native desktop packaging (e.g., Tauri) in later phases.

---

## 2. System Architecture Diagram

```
+-----------------------------------------------------------------------------------+
|                              USER ENVIRONMENT                                     |
|                                                                                   |
|  +-----------------------------------------------------------------------------+  |
|  |                   Presentation Layer (React 19 + Vite 8 + TS)               |  |
|  |                                                                             |  |
|  |  +---------------+  +--------------+  +------------+  +------------------+  |  |
|  |  |   Dashboard   |  | Memory Vault |  |   People   |  |    AI Studio     |  |  |
|  |  | (Stats/Recents|  | (Grid/List   |  |  (Lineage  |  |  (Local Model   |  |  |
|  |  |  /Storage)    |  |  /Filters)   |  |   Drawer)  |  |   Management)    |  |  |
|  |  +---------------+  +--------------+  +------------+  +------------------+  |  |
|  |  |         Tailwind CSS (Charcoal / Obsidian / Antique Gold)                 |  |
|  +-----------------------------------------------------------------------------+  |
|                                       |                                           |
|                           Local Loopback REST API                                 |
|                           (http://127.0.0.1:8000)                                 |
|                                       v                                           |
|  +-----------------------------------------------------------------------------+  |
|  |                      Application Layer (FastAPI Backend)                    |  |
|  |                                                                             |  |
|  |  +-----------------------------------------------------------------------+  |  |
|  |  | Routes: /health, /system/status, /memories, /tags, /people, /ai       |  |  |
|  |  +-----------------------------------------------------------------------+  |  |
|  |  | Ingestion Pipeline (backend/app/services/ingestion/):                  |  |  |
|  |  |   - validator.py         (Magic bytes, MIME spoofing, 100MB check)    |  |  |
|  |  |   - thumbnail_service.py (Pillow 480x480 thumbnail generation)        |  |  |
|  |  |   - image_processor.py   (Dimensions, EXIF date, GPS stripping)       |  |  |
|  |  |   - audio_processor.py   (Mutagen/wave duration, waveform peaks)      |  |  |
|  |  |   - video_processor.py   (Direct MP4 atom duration/dimension parser)  |  |  |
|  |  |   - document_processor.py(PDF pypdf, Word python-docx, UTF-8 text)    |  |  |
|  |  |   - metadata_extractor.py(Pipeline orchestrator)                      |  |  |
|  |  +-----------------------------------------------------------------------+  |  |
|  |  | Domain Services:                                                      |  |  |
|  |  |   - MemoryService  (Ingestion, filtering, pagination, search, patch)  |  |  |
|  |  |   - TagService     (CRUD, memory association counts)                  |  |  |
|  |  |   - PersonService  (Lineage, relationship indexing)                   |  |  |
|  |  |   - StorageService (Categorized directory management, containment)    |  |  |
|  |  |   - SystemService  (Direct SQLite metrics & storage diagnostics)      |  |  |
|  |  |   - OllamaService  (Non-blocking local neural model status)           |  |  |
|  |  |   - Speech Services (backend/app/services/speech/):                   |  |  |
|  |  |     • model_manager.py       (Offline Whisper discovery & downloads)  |  |  |
|  |  |     • audio_converter.py     (PyAV / Wave 16kHz mono resampling)      |  |  |
|  |  |     • transcription_engine.py(faster-whisper CPU int8 inference)      |  |  |
|  |  |     • diarization_engine.py  (20-D acoustic feature clustering)       |  |  |
|  |  |     • speaker_service.py     (Consent verification & voice profiles)  |  |  |
|  |  |     • job_worker.py          (Sequential persistent queue, restart)   |  |  |
|  |  +-----------------------------------------------------------------------+  |  |
|  +-----------------------------------------------------------------------------+  |
|                       |                                   |                       |
|           SQLAlchemy (WAL Mode)               Local HTTP (127.0.0.1:11434)        |
|                       v                                   v                       |
|  +------------------------------------+  +-------------------------------------+  |
|  |           Storage Layer            |  |         Local AI Runtime            |  |
|  |                                    |  |                                     |  |
|  |  - SQLite (digital_afterlife.db)   |  |  - Ollama Daemon                    |  |
|  |  - Categorized Storage:            |  |  - Target Model: qwen2.5:3b         |  |
|  |    data/memories/images/           |  |  - Standalone/Graceful Fallback     |  |
|  |    data/memories/audio/            |  +-------------------------------------+  |
|  |    data/memories/video/            |                                           |
|  |    data/memories/documents/        |                                           |
|  |    data/memories/stories/          |                                           |
|  |  - Thumbnails: data/thumbnails/    |                                           |
|  |  - Cache: data/cache/              |                                           |
|  +------------------------------------+                                           |
+-----------------------------------------------------------------------------------+
```

---

## 3. Subsystem Breakdown

### 3.1 Presentation Layer (`frontend/`)
- **Framework**: React 19 with Vite 8 and TypeScript.
- **Styling**: Tailwind CSS with custom dark obsidian and warm gold palette.
- **Views**:
  - **Memory Vault**: Grid / List view toggles, category filtering chips, people filter, tag filter, date range filter, sort order, and multi-field search.
  - **Media Previewers**: Interactive audio playback, video player, image viewer with thumbnail acceleration, and extracted document text viewer with one-click copy.
  - **Tag Management Modal**: Dedicated modal for creating, renaming, and deleting tags.
  - **Memory Detail Modal**: Viewing, editing (title, narrative notes, location, event date, privacy level, tags, people), downloading original artifacts, and permanent deletion with confirmation.

### 3.2 Ingestion Engine (`backend/app/services/ingestion/`)
- **`validator.py`**:
  - Inspects file magic byte headers (e.g. `\xFF\xD8\xFF` for JPEG, `\x89PNG` for PNG, `ID3`/`\xFF\xFB` for MP3, `ftyp` for MP4/M4A/MOV, `%PDF` for PDF, `PK\x03\x04` for DOCX).
  - Explicitly rejects executables (`MZ`, `\x7FELF`, Mach-O), HTML, PHP, and shell scripts.
  - Flags MIME spoofing where declared MIME contradicts binary signatures.
  - Rejects files exceeding the 100 MB configurable ceiling.
- **`thumbnail_service.py`**:
  - Automatically generates 480×480 JPEG thumbnails into `data/thumbnails/` for fast preview rendering.
- **`image_processor.py`**:
  - Extracts dimensions, parses safe EXIF capture dates, transposes orientation, enforces decompression bomb (`Image.MAX_IMAGE_PIXELS = 100M`) and 16,000px dimension limits, and strips GPS tags to preserve privacy. Original uploaded bytes are stored 100% unaltered.
- **`audio_processor.py`**:
  - Extracts duration in seconds, sample rates, and channels using Mutagen and Wave.
- **`video_processor.py`**:
  - Parses MP4/MOV container atoms (`mvhd`, `tkhd`) and WebM EBML elements (`\x1A\x45\xDF\xA3`) in pure Python to extract duration and resolution with zero FFmpeg dependencies.
- **`document_processor.py`**:
  - Performs clean, bounded text extraction (max 150,000 characters) on PDFs (`pypdf`), Word documents (`python-docx`), and text/Markdown files (`utf-8`). DOCX archives are deeply validated against path traversal and executable contents.

### 3.3 Storage Subsystem (`backend/app/services/storage_service.py`)
- Categorized subfolder organization:
  - `data/memories/images/`
  - `data/memories/audio/`
  - `data/memories/video/`
  - `data/memories/documents/`
  - `data/memories/stories/`
  - `data/thumbnails/`
  - `data/cache/`
- Containment verification: All file reads and writes verify that resolved paths reside inside the designated root directory, preventing directory traversal attacks.

### 3.4 Database Foundation (`backend/app/models/` & `session.py`)
- SQLite 3 with Write-Ahead Logging (`WAL` mode).
- Migration-safe auto-schema updater (`run_migrations`) that extends SQLite tables with new Phase 2 columns without data loss.
- Foreign keys, cascade rules, and indexes on `event_date`, `created_at`, `memory_type`, and `file_hash`.

### 3.5 Semantic Search & RAG Subsystem (`backend/app/services/rag/`)
- **Embedding Pipeline (`embedding_engine.py` & `model_manager.py`)**:
  - `intfloat/multilingual-e5-small` running locally on CPU via ONNX Runtime and Tokenizers.
  - Generates 384-dimensional normalized vector embeddings.
  - Strict task prefixing: `passage: ` for documents, `query: ` for search queries.
- **Persistent Vector Store (`vector_store.py`)**:
  - ChromaDB local PersistentClient at `data/vector_store/` with cosine metric space.
  - Fully ephemeral and derived from SQLite; never acts as source of truth.
- **Intelligent Chunker (`chunker.py`)**:
  - 400–600 token chunk target with 50–80 token overlap.
  - Preserves sentences in English and Hindi (`.`, `?`, `!`, `।`).
  - Preserves transcript timestamps (`start_time`, `end_time`) and speaker labels.
- **Hybrid Retrieval (`retrieval_service.py`)**:
  - Reciprocal Rank Fusion ($k=60$) combining semantic vector proximity and lexical SQLite matching.
  - Multi-attribute filtering (date range, person, memory type, tags, language).
  - Source diversification guard caps chunks per memory to prevent single-source monopolization.
- **Grounded Answer Generator (`rag_service.py`)**:
  - Integrates with local Ollama (`qwen2.5:3b`) using strict `<source_evidence>` XML boundaries.
  - Enforces non-fabrication, zero impersonation, and explicit abstention when evidence is insufficient.
  - Returns structured, verified citations that jump to original memories and seek audio/video playback to exact timestamps.

