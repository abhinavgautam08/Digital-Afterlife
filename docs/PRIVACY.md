# Privacy Policy & Ethical Architecture

**Application**: Digital Afterlife – Memory Keeper  
**Version**: 0.1.0  
**Phases Completed**: Phase 1: Foundation & Architecture, Phase 2: Memory Vault & Multimedia Preservation  

---

## 1. Core Ethical Tenet

> **"Your memories. Your machine. Your legacy."**

Digital Afterlife is conceived not as a SaaS platform or commercial cloud, but as a digital heirloom. Personal memories, family photographs, intimate voice recordings, and ancestral journals are among the most sensitive data a human being possesses. They must never become training fodder for remote AI companies, subject to cloud service shutdown, or exposed to third-party data breaches.

---

## 2. Privacy Guarantees

### Zero External Telemetry
- No usage analytics, trackers, cookies, or pingbacks exist anywhere in this codebase.
- No network requests are dispatched to external cloud servers, metrics aggregators, or logging collectors.

### Strict Local Loopback Binding
- By default, the FastAPI server binds exclusively to `127.0.0.1`.
- It does not listen on `0.0.0.0`, ensuring that other machines on the same local area network cannot access the API without explicit user configuration.

### EXIF Privacy & GPS Stripping
- Phase 2 image ingestion extracts safe capture dates (`DateTimeOriginal`) while strictly omitting GPS coordinates (`GPSInfo`) from stored metadata.
- This ensures personal residence locations and private coordinates are never inadvertently leaked in previews or metadata payloads.

### Local-Only Open-Weight AI
- All artificial intelligence inference is powered by local runtimes (Ollama) running open-weight models (such as Qwen 2.5 3B).
- Prompts, transcripts, and metadata never cross the machine's local loopback interface.
- Models are never downloaded silently in the background; user consent and explicit CLI execution (`ollama pull`) are required.

### Historical Provenance & Non-Fabrication
- The application enforces a strict distinction between authentic personal memories and AI-generated syntheses.
- AI features are designed to organize, search, and rediscover memories—never to hallucinate facts or present generated prose as authentic historical evidence.

---

## 3. Data Storage & Portability

- **Database**: SQLite database stored locally at `data/digital_afterlife.db`. Standard SQLite allows users to inspect, export, or back up their database using any open SQLite tool.
- **Physical Media**: Original files are saved in categorized directories inside `data/memories/{images,audio,video,documents,stories}/` using UUID-based internal identifiers while preserving original extension types and SHA-256 file integrity digests.
- **Thumbnails**: Optimized 480×480 JPEG thumbnails reside inside `data/thumbnails/` and are automatically deleted upon memory removal.
- **Backups**: To back up the entire Digital Afterlife vault, users simply need to copy the `data/` directory to an encrypted external drive or cold storage medium.

---

## 4. Encryption Architecture & At-Rest Storage Status

The codebase incorporates the `BaseEncryptionProvider` abstraction and SHA-256 cryptographic verification.
- **Current Phase 2 Status**: Uploaded files and SQLite records are stored in plaintext on local disk (`NoOpEncryptionProvider`). Physical access to the machine permits file inspection.
- **Future Security Phase Activation**: Files at rest will be protected by **AES-256-GCM** authenticated envelope encryption with key derivation interfaces designed for **Argon2id** / **PBKDF2** from a master passphrase known only to the user.

---

## 5. Biometric Voice Privacy & Consent (Phase 3)

### Mandatory Prior Consent
- No biometric voice signatures or speaker identification profiles may be generated or persisted without explicit, affirmative user consent stored in `speaker_consents`.
- Any enrollment attempt without recorded consent is hard-blocked with HTTP 403 Forbidden.

### Anonymous Diarization
- Oral history recordings are transcribed with anonymous speaker labels (`Speaker 1`, `Speaker 2`) by default, without attempting biometric correlation unless consented family profiles exist.

### Right to Complete Erasure
- Revoking consent via `POST /api/people/{id}/consent` (`consent_given=False`) or calling `DELETE /api/people/{id}/speaker-profile` permanently purges all acoustic feature vectors and mathematical voice signatures immediately from the database.
- Transcripts and audio files are decoupled from biometrics, ensuring family oral histories remain intact even if voice profiles are purged.

---

## 6. Semantic Search & Vector RAG Privacy Safeguards (Phase 4)

### Local Vector Containment
- Vector embeddings and nearest-neighbor indices reside strictly on local disk at `data/vector_store/` (ChromaDB Persistent Client).
- No memory text, search queries, or embeddings are transmitted to remote vector databases, hosted embedding APIs, or cloud platforms.

### Zero Silent Downloads
- The embedding model (`multilingual-e5-small`) and Ollama models (`qwen2.5:3b`) are never downloaded silently in the background. Downloads require explicit user confirmation via the UI or CLI.

### Biometric Segregation
- Speaker voice biometrics (acoustic vectors in `speaker_profiles`) are strictly segregated from the semantic memory vector store. Biometric voice signatures are NEVER indexed into ChromaDB or exposed to semantic search.

### Immediate Deletion Synchronization
- Deleting a memory permanently purges all associated vector chunks from ChromaDB immediately, preventing deleted memories from remaining retrievable through stale vectors.

### Prompt Injection Containment & Grounded Truth
- All retrieved memory excerpts are passed into local LLMs wrapped in `<source_evidence>` XML boundaries. Any malicious instructions or prompts within preserved historical documents are treated strictly as inert quotations.
- The assistant operates under a strict abstention mandate: if evidence is insufficient, it refuses to speculate.


