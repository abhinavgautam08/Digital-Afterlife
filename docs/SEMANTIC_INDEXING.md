# Semantic Indexing & Vector Store Lifecycle

**Application**: Digital Afterlife – Memory Keeper  
**Subsystem**: Persistent Vector Indexing Engine  
**Storage**: ChromaDB Local Persistent Client at `data/vector_store/`

---

## 1. Storage Philosophy: Derived vs. Authoritative

In **Digital Afterlife**, the vector store is explicitly classified as **derived, ephemeral cache data**.

* **Authoritative Source of Truth**:
  1. Original physical files (`data/memories/`)
  2. SQLite database records (`data/digital_afterlife.db`)
* **Derived Index**:
  1. ChromaDB vector database (`data/vector_store/`)
  2. Index tracking jobs (`indexing_jobs` table in SQLite)

If ChromaDB files are lost, corrupted, or deleted, **zero family data is lost**. The entire vector index can be reconstructed at any time via `POST /api/search/index/rebuild`.

---

## 2. Chunk Schema & Metadata Payload

Every vector chunk indexed in ChromaDB retains the following metadata:

| Key | Type | Description |
|---|---|---|
| `chunk_id` | `string` | Deterministic ID (e.g. `mem-uuid_document_0`) |
| `memory_id` | `string` | Foreign key to `memories.id` |
| `source_type` | `string` | `metadata`, `document`, `transcript`, or `description` |
| `original_filename` | `string` | Source filename (e.g. `1950_letter.pdf`) |
| `chunk_index` | `integer` | 0-indexed position within source |
| `content_hash` | `string` | SHA-256 hash of chunk content |
| `tags_csv` | `string` | Comma-separated tags |
| `person_ids_csv` | `string` | Comma-separated person IDs |
| `event_date` | `string` | ISO 8601 date string |
| `transcript_id` | `string` | Optional transcript ID |
| `start_time` | `float` | Start timestamp in seconds (-1 if non-transcript) |
| `end_time` | `float` | End timestamp in seconds (-1 if non-transcript) |
| `speaker_label` | `string` | Associated speaker label |

---

## 3. Incremental Indexing Lifecycle

```
[Memory Ingested or Edited]
            │
            ▼
Compute Content Hash (SHA-256)
            │
    Matches Stored Hash?
      ├── YES ──► Skip Indexing (Status: 'skipped')
      │
      └── NO ───► Extract Text & Transcript Segments
                  Generate Chunks (MemoryChunker)
                  Embed with E5 'passage: ' prefix
                  Delete Old Vectors for Memory ID
                  Upsert New Vectors in ChromaDB
                  Update IndexingJob (Status: 'completed')
```

### Deletion Synchronization
When a memory is deleted via `DELETE /api/memories/{id}`:
1. `vector_store.delete_by_memory_id(memory_id)` immediately purges all associated chunks from ChromaDB.
2. The SQLite tracking record in `indexing_jobs` is removed.
3. Physical files and thumbnails are unlinked.

---

## 4. Rebuild & Disaster Recovery

If the vector database is corrupted or the user chooses to switch embedding models:
- **API Endpoint**: `POST /api/search/index/rebuild`
- **CLI / Python Procedure**:
  ```python
  from backend.app.database.session import SessionLocal
  from backend.app.services.rag.indexing_service import indexing_service

  db = SessionLocal()
  report = indexing_service.rebuild_index(db)
  print(report)
  ```
- **Operations Performed**:
  1. Purges existing ChromaDB collection `memory_chunks`.
  2. Resets `indexing_jobs` table.
  3. Iterates over all active SQLite memories and re-indexes them sequentially.

