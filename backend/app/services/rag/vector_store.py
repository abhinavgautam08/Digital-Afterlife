"""
Persistent ChromaDB Vector Store for Digital Afterlife.
Stores and indexes embedded memory chunks strictly on local disk at `data/vector_store/`.
Supports metadata filtering (date, person, type, tags) and deduplication.
"""
from pathlib import Path
from typing import List, Dict, Any, Optional
import shutil

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.services.rag.chunker import MemoryChunk


class VectorStoreService:
    COLLECTION_NAME = "memory_chunks"

    def __init__(self, persist_dir: Optional[Path] = None):
        self.persist_dir = persist_dir or settings.VECTOR_STORE_DIR
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self._client = None
        self._collection = None

    def _get_client(self):
        if self._client is None:
            try:
                import chromadb
                from chromadb.config import Settings as ChromaSettings

                self._client = chromadb.PersistentClient(
                    path=str(self.persist_dir),
                    settings=ChromaSettings(
                        anonymized_telemetry=False,
                        allow_reset=True,
                        is_persistent=True,
                    )
                )
            except Exception as e:
                logger.error(f"Failed to initialize ChromaDB PersistentClient: {e}")
                raise RuntimeError(f"ChromaDB initialization failed: {e}")
        return self._client

    def _get_collection(self):
        if self._collection is None:
            client = self._get_client()
            expected_meta = {
                "hnsw:space": "cosine",
                "model_name": settings.EMBEDDING_DEFAULT_MODEL,
                "dimension": settings.EMBEDDING_DIMENSION
            }
            try:
                # Check for existing collection and model compatibility
                try:
                    existing = client.get_collection(name=self.COLLECTION_NAME)
                    meta = existing.metadata or {}
                    existing_model = meta.get("model_name")
                    existing_dim = meta.get("dimension")

                    if (existing_model and existing_model != settings.EMBEDDING_DEFAULT_MODEL) or \
                       (existing_dim and existing_dim != settings.EMBEDDING_DIMENSION):
                        logger.warning(
                            f"Incompatible embedding model detected in ChromaDB (found model='{existing_model}', "
                            f"dim={existing_dim}; expected model='{settings.EMBEDDING_DEFAULT_MODEL}', "
                            f"dim={settings.EMBEDDING_DIMENSION}). Resetting vector collection to prevent corruption."
                        )
                        client.delete_collection(self.COLLECTION_NAME)
                        self._collection = client.create_collection(
                            name=self.COLLECTION_NAME,
                            metadata=expected_meta
                        )
                    else:
                        self._collection = existing
                except Exception:
                    # Collection does not exist yet; create fresh
                    self._collection = client.create_collection(
                        name=self.COLLECTION_NAME,
                        metadata=expected_meta
                    )
            except Exception as e:
                logger.error(f"Failed to get/create ChromaDB collection '{self.COLLECTION_NAME}': {e}")
                raise RuntimeError(f"ChromaDB collection error: {e}")
        return self._collection

    def count(self) -> int:
        """Returns the total number of indexed vector chunks."""
        try:
            coll = self._get_collection()
            return coll.count()
        except Exception as e:
            logger.debug(f"Vector store count error: {e}")
            return 0

    def add_chunks(self, chunks: List[MemoryChunk], embeddings: List[List[float]]) -> int:
        """Upserts a batch of chunks and their embedding vectors into the vector store."""
        from backend.app.core.crypto import vault_key_manager, VaultLockedError
        if vault_key_manager.is_initialized() and not vault_key_manager.is_unlocked():
            raise VaultLockedError("Vault is locked. Cannot query or modify vector store.")

        if not chunks:
            return 0
        if len(chunks) != len(embeddings):
            raise ValueError("Chunks and embeddings length mismatch.")

        coll = self._get_collection()

        ids = [c.chunk_id for c in chunks]
        documents = [c.text for c in chunks]
        metadatas = []

        for c in chunks:
            meta = {
                "memory_id": c.memory_id,
                "source_type": c.source_type,
                "original_filename": c.original_filename,
                "chunk_index": c.chunk_index,
                "content_hash": c.content_hash,
                "tags_csv": ",".join(c.tags) if c.tags else "",
                "person_ids_csv": ",".join(c.person_ids) if c.person_ids else "",
                "event_date": c.event_date or "",
                "transcript_id": c.transcript_id or "",
                "start_time": float(c.start_time) if c.start_time is not None else -1.0,
                "end_time": float(c.end_time) if c.end_time is not None else -1.0,
                "speaker_label": c.speaker_label or "",
            }
            metadatas.append(meta)

        try:
            coll.upsert(
                ids=ids,
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas
            )
            return len(chunks)
        except Exception as e:
            logger.error(f"Failed to upsert chunks into ChromaDB: {e}")
            raise

    def query(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        where_filter: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Queries the vector collection for nearest neighbors.
        Returns formatted result records with similarity scores in [0.0, 1.0].
        """
        from backend.app.core.crypto import vault_key_manager, VaultLockedError
        if vault_key_manager.is_initialized() and not vault_key_manager.is_unlocked():
            raise VaultLockedError("Vault is locked. Cannot query or modify vector store.")

        try:
            coll = self._get_collection()
            total_items = coll.count()
            if total_items == 0:
                return []

            effective_k = min(top_k, total_items)
            res = coll.query(
                query_embeddings=[query_embedding],
                n_results=effective_k,
                where=where_filter if where_filter else None
            )

            results: List[Dict[str, Any]] = []
            if not res or not res.get("ids") or not res["ids"][0]:
                return []

            ids = res["ids"][0]
            docs = res["documents"][0] if res.get("documents") else []
            metadatas = res["metadatas"][0] if res.get("metadatas") else []
            distances = res["distances"][0] if res.get("distances") else []

            for i, chunk_id in enumerate(ids):
                dist = distances[i] if i < len(distances) else 1.0
                # In cosine space, distance in [0, 2]. Similarity = max(0.0, 1.0 - dist)
                similarity = max(0.0, min(1.0, 1.0 - (dist / 2.0)))
                meta = metadatas[i] if i < len(metadatas) else {}

                tags_raw = meta.get("tags_csv", "")
                tags_list = [t for t in tags_raw.split(",") if t] if tags_raw else []

                person_ids_raw = meta.get("person_ids_csv", "")
                person_list = [p for p in person_ids_raw.split(",") if p] if person_ids_raw else []

                start_t = meta.get("start_time", -1.0)
                end_t = meta.get("end_time", -1.0)

                results.append({
                    "chunk_id": chunk_id,
                    "memory_id": meta.get("memory_id", ""),
                    "source_type": meta.get("source_type", ""),
                    "original_filename": meta.get("original_filename", ""),
                    "chunk_index": meta.get("chunk_index", 0),
                    "text": docs[i] if i < len(docs) else "",
                    "similarity": round(similarity, 4),
                    "distance": round(dist, 4),
                    "tags": tags_list,
                    "person_ids": person_list,
                    "event_date": meta.get("event_date") or None,
                    "transcript_id": meta.get("transcript_id") or None,
                    "start_time": start_t if start_t >= 0 else None,
                    "end_time": end_t if end_t >= 0 else None,
                    "speaker_label": meta.get("speaker_label") or None,
                })

            return results
        except Exception as e:
            logger.error(f"Error querying ChromaDB: {e}")
            return []

    def delete_by_memory_id(self, memory_id: str) -> int:
        """Removes all indexed chunks associated with a given memory ID."""
        try:
            coll = self._get_collection()
            # Find matching IDs first
            res = coll.get(where={"memory_id": memory_id})
            ids_to_delete = res.get("ids", [])
            if ids_to_delete:
                coll.delete(ids=ids_to_delete)
                logger.info(f"Purged {len(ids_to_delete)} vector chunks for memory '{memory_id}'.")
                return len(ids_to_delete)
            return 0
        except Exception as e:
            logger.error(f"Failed to delete chunks for memory '{memory_id}' in ChromaDB: {e}")
            return 0

    def reset(self):
        """Clears all vectors from ChromaDB for full rebuild."""
        try:
            client = self._get_client()
            try:
                client.delete_collection(self.COLLECTION_NAME)
            except Exception:
                pass
            self._collection = None
            logger.info("ChromaDB collection reset successfully.")
        except Exception as e:
            logger.error(f"Failed to reset ChromaDB collection: {e}")
            # If filesystem is corrupted, remove and recreate directory
            self._client = None
            self._collection = None
            if self.persist_dir.exists():
                shutil.rmtree(self.persist_dir, ignore_errors=True)
                self.persist_dir.mkdir(parents=True, exist_ok=True)

    def get_status(self) -> Dict[str, Any]:
        """Reports health and statistics of the local vector store."""
        try:
            count = self.count()
            return {
                "status": "online",
                "healthy": True,
                "vector_count": count,
                "persist_directory": str(self.persist_dir),
                "collection_name": self.COLLECTION_NAME,
            }
        except Exception as e:
            return {
                "status": "degraded",
                "healthy": False,
                "vector_count": 0,
                "persist_directory": str(self.persist_dir),
                "collection_name": self.COLLECTION_NAME,
                "error": str(e),
            }


vector_store = VectorStoreService()

