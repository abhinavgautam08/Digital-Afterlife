---
title: "Digital Afterlife: A Local, Sovereign Memory Vault & Digital Ofrenda for Honoring Ancestors"
published: false
description: "Preserve family oral histories, letters, photographs, and memories with 100% offline open-weight AI, zero-knowledge encryption, and digital remembrance pages."
tags: "hf26challenge, opensource, ai, privacy"
canonical_url: false
cover_image: https://dev-to-uploads.s3.us-east-2.amazonaws.com/uploads/events/cover_image/82/e4131c99-f797-42be-95ef-b55e1f04255f.png
---

*This article is submitted to the **Hacktoberfest Open-Source AI Challenge: Week 4** (#hf26challenge).*

---

## 1. What I Built

**Digital Afterlife — Memory Keeper** is a local, offline-first, sovereign family memory vault and digital remembrance builder (*digital ofrenda*).

In an era where family photos, voice memos, and historical letters are routinely entrusted to commercial cloud providers that monetize data, change pricing, shut down services, or lock families out, **Digital Afterlife** guarantees permanent, sovereign preservation:

- **100% Local Execution**: Speech-to-text, speaker diarization, vector search, RAG question answering, and biography generation run on your own machine without a single byte leaving the host.
- **Multimedia Memory Vault**: Ingests, validates, deduplicates, and organizes 17 distinct file extensions across photographs, audio recordings, family videos, documents, and written memoirs.
- **Local Speech-to-Text & Diarization**: Transcribes oral histories on CPU using `faster-whisper` quantized to `int8`, clustering acoustic features into anonymous speaker labels with strict biometric consent enforcement.
- **Local Semantic Search & RAG**: Indexes documents and transcripts using `multilingual-e5-small` in ChromaDB with Reciprocal Rank Fusion (RRF) hybrid retrieval and Ollama (`qwen2.5:3b`) grounded generation.
- **Digital Ofrenda & Storytelling**: Synthesizes verified multi-chapter biographies, interactive life timelines, curated collections, and dedicated **Remembrance Pages** that celebrate departed loved ones.
- **Zero-Knowledge Encryption**: Full AES-256-GCM chunked streaming encryption, Argon2id key derivation, authenticated database field encryption, and auto-locking vault controls.

---

## 2. Interpretation of the Theme: "Ghost in the Machine"

Week 4's theme asks us to *"build something spooky, or something that honors the past in the spirit of Día de los Muertos, with open-weight models or open-source AI."*

Between October 31 (Halloween) and November 1–2 (Día de los Muertos), we reflect on the memories and stories of those who came before us. Día de los Muertos is not about fear; it is about keeping loved ones alive in our collective memory through *ofrendas* adorned with photographs, personal reflections, favorite memories, and stories.

**Digital Afterlife transforms the "ghost in the machine" from a metaphor of eerie surveillance into an act of enduring remembrance:**
- **The Digital Ofrenda**: Users create dedicated **Remembrance Pages** for departed ancestors, curating their favorite photographs, handwritten recipes, oral memories, and personal tributes.
- **Interactive Life Timelines**: Reconstructs an ancestor's life journey chronologically, linking milestone memories across generations.
- **Oral History Preservation**: Allows elders to record voice memories that are transcribed locally, ensuring their spoken words, vernacular, and cadence remain preserved forever.
- **Ethical Grounding**: The AI is strictly prohibited from inventing unrecorded memories or fabricating quotes. It acts solely as an evidence-grounded custodian of authentic family truth.

---

## 3. Demo & Walkthrough

Because Digital Afterlife is an air-gapped, privacy-first local application, there is no public web-hosted server tracking users. The walkthrough below illustrates the primary local workflows:

### A. The Memory Vault
Users upload photographs, audio interviews, scanned documents, and home videos. EXIF GPS coordinates are automatically stripped for family privacy while capture dates and metadata are indexed.

### B. Speech-to-Text & Interactive Audio Timeline
An audio recording of a grandparent telling a childhood story is queued. The local `faster-whisper` engine transcribes the audio, detects the language, and partitions segments. Users click timestamp chips (`[▶ 00:15 - 00:32]`) to seek audio playback directly.

### C. Ask Your Memories (Semantic RAG)
Users ask: *"Where did grandfather live before moving to the city?"*
The system performs hybrid vector + lexical retrieval, extracting verifiable excerpts from scanned letters and transcripts, answering with direct citations that link back to the source documents.

### D. Remembrance Page (Digital Ofrenda)
Visiting a departed relative's Remembrance Page presents a commemorative shrine featuring:
- Hero portrait and biographical summary
- Favorite memories and milestone events
- Personal tributes and family notes
- Direct links to original voice recordings and letters

### E. Vault Lock & Zeroization
Clicking **Lock Vault** zeroes the Data Encryption Key in memory. All sensitive endpoints return `HTTP 423 Locked`. The vault remains inaccessible until unlocked with the master password or 32-character recovery key.

---

## 4. How I Built It

Digital Afterlife is built with an open-source, offline-first technology stack:

```
┌────────────────────────────────────────────────────────┐
│            Frontend (React 19, TypeScript, Vite)       │
│      Dark Obsidian & Gold UI • Lucide • Tailwind CSS   │
└───────────────────────────┬────────────────────────────┘
                            │ (Local HTTP 127.0.0.1:8000)
┌───────────────────────────▼────────────────────────────┐
│                  Backend (FastAPI, Python 3.12)        │
├────────────────────────────────────────────────────────┤
│  Security & Crypto: AES-256-GCM Streaming, Argon2id    │
│  Speech Engine: faster-whisper (CPU int8), PyAV        │
│  Semantic Search: multilingual-e5-small (ONNX)         │
│  Local RAG: ChromaDB + Ollama (Qwen 2.5 3B Instruct)   │
│  Database: SQLite (WAL mode, authenticated fields)     │
└────────────────────────────────────────────────────────┘
```

### Key Technical Implementations
1. **Streaming AES-256-GCM (`FileEncryptor`)**: Media files are encrypted in 64 KB chunks (`DAENC1` format) with derived nonces (`base_nonce XOR chunk_index`) and AAD chunk position binding to prevent tampering, truncation, or chunk reordering.
2. **Field-Level Encryption (`FieldCipher`)**: SQLite sensitive text columns (`description`, `extracted_text`, `transcript_text`, `content`) are encrypted in `ENC:v1:` authenticated envelopes.
3. **Argon2id Key Derivation**: High-cost key derivation (`m=64MB, t=3, p=4`) protects the master passphrase and generates a 128-bit emergency recovery key.
4. **Biometric Consent Framework**: Biometric speaker profiles cannot be created without prior explicit consent (`SpeakerConsent`), and revoking consent immediately purges acoustic vectors.
5. **Unified Encrypted Backups**: Backups bundle the database, security envelope, and media into an encrypted `.da-backup` archive created entirely in RAM (`io.BytesIO`), leaving no unencrypted temp files on disk.

---

## 5. Why Open Innovation Matters

Why does open innovation matter for preserving family memories?

1. **Permanence Without Subscription Hostage**: Commercial genealogy and photo platforms frequently pivot, raise subscription rates, or shut down. If a company goes out of business, family memories can disappear. Open-source software running open-weight models on standard consumer hardware lasts as long as your hardware does.
2. **Absolute Personal Privacy**: Family memories include birth certificates, handwritten love letters, sensitive photographs, medical records, and voice signatures. Entrusting these to cloud AI APIs means submitting family intimate histories to corporate servers. Open innovation lets families run state-of-the-art AI on their own machines without sacrificing privacy.
3. **Works With the Lights (and Internet) Off**: Digital Afterlife runs without an active internet connection. In remote areas, during network outages, or on air-gapped computers, your legacy remains accessible.
4. **Data Sovereignty**: Your memories are stored in open formats (SQLite, standard media, JSON envelopes) with exportable encrypted backups. You own your data completely.

---

## 6. Testing & Verification Instructions for Judges

To verify the project locally:

### 1. Prerequisites
- Python 3.12+
- Node.js 18+
- Git

### 2. Setup
```bash
# Clone the repository
git clone https://github.com/abhinavgautam08/digital-afterlife.git
cd digital-afterlife

# Setup backend
backend\.venv\Scripts\activate      # or python -m venv .venv
pip install -r backend/requirements.txt
python scripts/init_db.py

# Setup frontend
cd frontend
npm install
```

### 3. Run Automated Regression Test Suite
Run the full backend test suite (**132 passing tests**):
```bash
backend\.venv\Scripts\pytest.exe -v
```

Verify frontend build:
```bash
cd frontend
npm run build
```

### 4. Launch Application
- **Backend:** `uvicorn backend.app.main:app --host 127.0.0.1 --port 8000`
- **Frontend:** `npm run dev` in `frontend/`
- Open `http://127.0.0.1:5173`.
- Test vault setup at `/settings`, create a remembrance page, upload an oral history, and test locking/unlocking.

---

## 7. Links & Repository

- **GitHub Repository**: [https://github.com/abhinavgautam08/digital-afterlife](https://github.com/abhinavgautam08/digital-afterlife)
- **License**: MIT License (Open Source)
- **Built for**: Hacktoberfest 2026 Week 4 DEV Challenge (#hf26challenge)

