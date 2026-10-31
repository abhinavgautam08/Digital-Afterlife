# REST API Specification: Digital Afterlife (Phases 1 & 2)

**Base URL**: `http://127.0.0.1:8000/api`  
**Interactive Docs**: `http://127.0.0.1:8000/api/docs` (Swagger UI)  
**ReDoc**: `http://127.0.0.1:8000/api/redoc`  

---

## 1. System & Health

### `GET /health`
Returns application health, version, and database connectivity.

**Response `200 OK`**:
```json
{
  "status": "healthy",
  "app": "Digital Afterlife – Memory Keeper",
  "version": "0.1.0",
  "database": "connected",
  "ai_service": "offline"
}
```

---

### `GET /system/status`
Calculates live metrics computed directly from SQLite and physical storage paths.

**Response `200 OK`**:
```json
{
  "application_name": "Digital Afterlife – Memory Keeper",
  "version": "0.1.0",
  "environment": "development",
  "privacy_mode": "Strict Offline-First (No External Telemetry)",
  "database_connected": true,
  "ai_status": "offline",
  "storage": {
    "storage_directory": "D:\\Digital Afterlife\\data\\memories",
    "total_files": 14,
    "total_bytes": 2450284,
    "formatted_size": "2.3 MB"
  },
  "statistics": {
    "total_memories": 10,
    "photographs": 5,
    "audio_recordings": 2,
    "documents": 2,
    "stories": 0,
    "videos": 1,
    "total_people": 4
  }
}
```

---

## 2. Memory Vault

### `GET /memories`
Lists preserved memory artifacts with pagination, multi-criteria filtering, and sorting.

**Query Parameters**:
- `page` (integer, default: 1): Page number.
- `size` (integer, default: 12, max: 100): Items per page.
- `search` (string, optional): Search term matched across title, description, location, and extracted document text.
- `memory_type` (string, optional): Filter by `photograph`, `audio`, `video`, `document`, or `story`.
- `person_id` (string, optional): Filter by associated person UUID.
- `tag` (string, optional): Filter by tag name (case-insensitive).
- `date_from` (ISO datetime string, optional): Filter memories on or after this event date / ingestion date.
- `date_to` (ISO datetime string, optional): Filter memories on or before this event date / ingestion date.
- `sort_by` (string, default: `created_at_desc`): Sort order (`created_at_desc`, `created_at_asc`, `event_date_desc`, `event_date_asc`, `title_asc`, `size_desc`).

**Response `200 OK`**:
```json
{
  "items": [
    {
      "id": "c1f7a049-51a7-4740-9a2c-9a1c1d42858b",
      "title": "Summer Cabin 1984",
      "description": "Family trip to Lake Tahoe.",
      "memory_type": "photograph",
      "original_filename": "lake_tahoe.jpg",
      "stored_filename": "c1f7a04951a747409a2c9a1c1d42858b.jpg",
      "mime_type": "image/jpeg",
      "file_size": 2048500,
      "sha256_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      "width": 1920,
      "height": 1080,
      "duration_seconds": null,
      "extracted_text": null,
      "thumbnail_path": "c1f7a04951a747409a2c9a1c1d42858b_thumb.jpg",
      "has_thumbnail": true,
      "location": "Lake Tahoe, CA",
      "original_created_at": "1984-07-15T14:30:00",
      "processing_status": "completed",
      "processing_error": null,
      "created_at": "2026-10-31T12:00:00Z",
      "updated_at": "2026-10-31T12:00:00Z",
      "event_date": "1984-07-15T00:00:00Z",
      "privacy_level": "private",
      "people": [
        { "id": "p1", "full_name": "Eleanor Vance", "relationship": "Grandmother" }
      ],
      "tags": [
        { "id": "t1", "name": "travel" },
        { "id": "t2", "name": "family" }
      ],
      "transcripts": []
    }
  ],
  "total": 1,
  "page": 1,
  "size": 12,
  "total_pages": 1
}
```

---

### `POST /memories`
Uploads and preserves a new multimedia memory artifact. Validates file signatures, detects MIME spoofing, generates thumbnails, parses EXIF / metadata, extracts document text, and verifies SHA-256 uniqueness.

**Form Data Fields**:
- `file` (UploadFile, required): The multimedia file (max 100 MB streaming limit; 17 supported extensions: .jpg, .jpeg, .png, .webp, .gif, .mp3, .wav, .m4a, .ogg, .flac, .mp4, .webm, .mov, .pdf, .docx, .txt, .md).
- `title` (string, required): Artifact title.
- `memory_type` (string, required): `photograph`, `audio`, `video`, `document`, or `story`.
- `description` (string, optional): Narrative notes or context.
- `event_date` (string, optional): ISO date or `YYYY-MM-DD`.
- `location` (string, optional): Place or geographic context.
- `privacy_level` (string, default: `private`): `private`, `family`, or `public`.
- `person_ids` (string, optional): JSON list or comma-separated UUIDs of connected individuals.
- `tags` (string, optional): Comma-separated list of tags.

**Error Status Codes**:
- `400 Bad Request`: File fails magic byte validation, is corrupted/malformed, or exceeds 100 MB.
- `409 Conflict`: Identical file already exists (duplicate SHA-256 hash).

---

### `GET /memories/{id}`
Retrieves complete metadata for a single memory artifact.

---

### `PATCH /memories/{id}`
Updates editable memory metadata (title, narrative description, location, event date, privacy level, connected people, and tags).

**Request Body**:
```json
{
  "title": "Summer Cabin 1984 (Restored)",
  "description": "Updated notes with Grandma Eleanor's recollections.",
  "location": "Lake Tahoe, California",
  "event_date": "1984-07-15",
  "privacy_level": "family",
  "person_ids": ["p1", "p2"],
  "tags": ["travel", "family", "vacation"]
}
```

---

### `DELETE /memories/{id}`
Permanently deletes the memory record, associations, thumbnail, and the physical artifact from disk.

---

### `GET /memories/{id}/file`
Streams the original binary file with appropriate MIME headers and range support for media players.

---

### `GET /memories/{id}/thumbnail`
Streams the optimized 480×480 JPEG thumbnail generated during ingestion.

---

### `GET /memories/search`
Quick multi-attribute search across title, description, location, and extracted text.

**Query Parameters**:
- `q` (string, required): Search query.
- `limit` (integer, default: 20): Maximum results.

---

## 3. Tag Management

### `GET /tags`
Lists all tags sorted alphabetically, along with count of linked memories.

**Response `200 OK`**:
```json
[
  { "id": "t1", "name": "childhood", "memories_count": 4 },
  { "id": "t2", "name": "travel", "memories_count": 2 }
]
```

### `POST /tags`
Creates a new tag.

**Request Body**:
```json
{ "name": "Recipe" }
```

### `PATCH /tags/{id}`
Renames an existing tag.

**Request Body**:
```json
{ "name": "Heirloom Recipes" }
```

### `DELETE /tags/{id}`
Deletes a tag and removes all memory associations.

---

## 4. People & Lineage Directory

### `GET /people`
Lists all family members with counts of associated memories.

### `POST /people`
Registers a new individual.

**Request Body**:
```json
{
  "full_name": "Eleanor Vance",
  "relationship": "Grandmother",
  "biography": "Born in 1928, schoolteacher and avid botanist."
}
```

### `GET /people/{id}/memories`
Lists all memories associated with a specific individual.

---

## 5. Local AI Studio (Ollama)

### `GET /ai/status`
Checks the state of the local Ollama daemon and configured model.

### `GET /ai/models`
Lists all locally installed models on the host machine.

---

## 6. Local Speech-to-Text & Diarization (Phase 3)

### `POST /memories/{id}/transcription`
Submits an audio or video memory for offline speech-to-text transcription and diarization.

**Request Body**:
```json
{
  "model_name": "base",
  "language": "auto",
  "enable_diarization": true
}
```
**Response `202 Accepted`**:
```json
{
  "id": "job-uuid",
  "memory_id": "memory-uuid",
  "status": "queued",
  "progress": 0.0,
  "current_stage": "Queued",
  "model_name": "base",
  "language": "auto",
  "enable_diarization": true,
  "created_at": "2026-10-31T14:00:00Z"
}
```

### `GET /transcription/jobs`
Lists recent transcription jobs with optional query filters (`memory_id`, `status`).

### `GET /transcription/jobs/{id}`
Returns granular progress and stage information for a job.

### `POST /transcription/jobs/{id}/cancel`
Cancels a queued or active transcription job.

### `GET /memories/{id}/transcript`
Fetches the complete transcript and timestamped speaker segments for a memory.

**Response `200 OK`**:
```json
{
  "id": "transcript-uuid",
  "memory_id": "memory-uuid",
  "language": "en",
  "detected_language": "en",
  "model_name": "base",
  "processing_duration": 4.12,
  "transcript_text": "We built this family house in nineteen sixty two.",
  "segments": [
    {
      "id": "segment-uuid",
      "transcript_id": "transcript-uuid",
      "start_time": 0.0,
      "end_time": 3.8,
      "text": "We built this family house in nineteen sixty two.",
      "speaker_label": "Speaker 1",
      "speaker_id": null,
      "confidence": 0.94,
      "segment_order": 0
    }
  ]
}
```

### `PATCH /transcripts/{id}`
Updates transcript text or individual segment fields (text, speaker_label, speaker_id).

### `DELETE /transcripts/{id}`
Permanently deletes transcript and cascade-deletes all segments.

### `GET /transcription/models`
Lists supported Whisper models (`tiny`, `base`, `small`) with local installation and download status.

### `POST /transcription/models/download`
Explicitly triggers model download into local storage.

### `DELETE /transcription/models/{model_name}`
Deletes a locally downloaded model to reclaim disk space.

### `GET /transcription/status`
Returns compute architecture (`cpu`, `int8`), worker threads, and queue telemetry.

---

## 7. Speaker Consent & Voice Profiles (Phase 3)

### `GET /people/{id}/consent`
Retrieves affirmative consent record for biometric voice analysis.

### `POST /people/{id}/consent`
Records or revokes consent. Revoking consent immediately purges enrolled voice profiles.

**Request Body**:
```json
{
  "consent_given": true,
  "consent_notes": "Oral history preservation consent agreement signed"
}
```

### `GET /people/{id}/speaker-profile`
Retrieves metadata of the enrolled voice profile.

### `POST /people/{id}/speaker-profile/enroll`
Enrolls a voice sample for a person from an audio memory. **Requires prior affirmative consent (HTTP 403 otherwise).**

### `DELETE /people/{id}/speaker-profile`
Deletes the voice profile and purges acoustic feature vectors permanently.

---

## 8. Semantic Search & RAG (Phase 4)

### `POST /search/semantic`
Performs pure multilingual semantic search over indexed memory vector chunks.

**Request Body**:
```json
{
  "query": "Where did grandfather work?",
  "top_k": 5,
  "date_from": "1960-01-01T00:00:00",
  "person_id": "person-uuid"
}
```

### `POST /search/hybrid`
Executes hybrid retrieval combining semantic similarity and SQLite lexical matching via Reciprocal Rank Fusion (RRF).

### `POST /memories/ask`
Asks a natural language question about family memories. Returns a grounded answer synthesized exclusively from retrieved evidence, along with structured source citations.

**Request Body**:
```json
{
  "query": "What did grandmother say about the orchard?",
  "retrieval_mode": "hybrid",
  "top_k": 5
}
```

**Response `200 OK`**:
```json
{
  "answer": "In her 1985 oral history interview, grandmother recalled planting the mango orchard behind the ancestral house in 1952 [1].",
  "evidence_status": "grounded",
  "citations": [
    {
      "index": 1,
      "memory_id": "memory-uuid",
      "title": "Grandmother Interview 1985",
      "source_type": "transcript",
      "memory_type": "audio",
      "original_filename": "interview.wav",
      "excerpt": "[Grandma]: We planted the mango orchard in 1952...",
      "start_time": 15.2,
      "end_time": 24.8,
      "speaker_label": "Grandma",
      "similarity": 0.88
    }
  ],
  "query": "What did grandmother say about the orchard?",
  "retrieval_mode": "hybrid",
  "sources_retrieved_count": 1,
  "model_name": "qwen2.5:3b",
  "processing_time_seconds": 1.42
}
```

### `GET /search/index/status`
Reports SQLite-to-ChromaDB synchronization state, vector counts, and pending jobs.

### `POST /search/index/rebuild`
Purges ChromaDB and re-indexes all active memories in SQLite.

### `POST /search/index/retry`
Retries previously failed indexing jobs.

### `GET /search/models`
Lists supported local embedding models with installation status.

### `POST /search/models/download`
Explicitly triggers downloading embedding model weights (`multilingual-e5-small`). Zero silent downloads.


