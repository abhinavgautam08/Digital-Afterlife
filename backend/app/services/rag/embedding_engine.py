"""
Local Embedding Engine for Semantic Memory Search.
Implements the E5 embedding standard:
  - Passages: 'passage: <text>'
  - Search Queries: 'query: <text>'
Runs strictly on local CPU with ONNX Runtime and Tokenizers.
Includes a deterministic MockEmbeddingEngine for fast, offline testing.
"""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Union, Optional
import hashlib
import numpy as np

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.services.rag.model_manager import (
    embedding_model_manager,
    ModelNotInstalledError,
    ModelCorruptError,
)


class BaseEmbeddingEngine(ABC):
    """Abstract interface for local text embedding models."""

    @abstractmethod
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embeds a batch of documents or passages with 'passage: ' prefix."""
        pass

    @abstractmethod
    def embed_query(self, query: str) -> List[float]:
        """Embeds a search query with 'query: ' prefix."""
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Returns the embedding vector dimension."""
        pass


class MockEmbeddingEngine(BaseEmbeddingEngine):
    """
    Deterministic pseudo-embedding engine for tests and offline mode.
    Maps arbitrary text (English, Hindi, symbols) to a normalized 384-D vector.
    Similar texts produce similar vectors via n-gram hash accumulation.
    """

    def __init__(self, dimension: int = 384):
        self._dimension = dimension

    @property
    def dimension(self) -> int:
        return self._dimension

    def _hash_to_vector(self, text: str) -> List[float]:
        if not text or not text.strip():
            return [0.0] * self._dimension

        vec = np.zeros(self._dimension, dtype=np.float32)
        clean = text.strip().lower()

        # Generate deterministic feature frequencies from n-grams and words
        words = clean.split()
        for i, word in enumerate(words):
            h = int(hashlib.md5(word.encode("utf-8", errors="ignore")).hexdigest(), 16)
            idx = h % self._dimension
            sign = 1.0 if (h >> 8) % 2 == 0 else -1.0
            vec[idx] += sign * (1.0 + (i % 3) * 0.2)

        # Also hash 3-grams for subword similarity (vital for Hindi / morphologically rich words)
        for i in range(max(1, len(clean) - 2)):
            tri = clean[i:i+3]
            h = int(hashlib.sha256(tri.encode("utf-8", errors="ignore")).hexdigest(), 16)
            idx = h % self._dimension
            vec[idx] += 0.5 * (1.0 if (h >> 4) % 2 == 0 else -1.0)

        # L2 normalize
        norm = np.linalg.norm(vec)
        if norm > 1e-9:
            vec = vec / norm
        else:
            vec[0] = 1.0
        return vec.tolist()

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        # Enforce E5 passage prefix if not present
        prefixed = [t if t.startswith("passage: ") else f"passage: {t}" for t in texts]
        return [self._hash_to_vector(t) for t in prefixed]

    def embed_query(self, query: str) -> List[float]:
        # Enforce E5 query prefix if not present
        prefixed = query if query.startswith("query: ") else f"query: {query}"
        return self._hash_to_vector(prefixed)


class ONNXEmbeddingEngine(BaseEmbeddingEngine):
    """
    Local ONNX Runtime embedding engine targeting intfloat/multilingual-e5-small.
    Runs on CPU without PyTorch overhead.
    """

    def __init__(self, model_name: str = "multilingual-e5-small"):
        self.model_name = model_name
        self._session = None
        self._tokenizer = None
        self._dimension = 384
        self._model_dir: Optional[Path] = None

    @property
    def dimension(self) -> int:
        return self._dimension

    def _load_engine(self):
        if self._session is not None and self._tokenizer is not None:
            return

        model_dir = embedding_model_manager.ensure_model_available(self.model_name)
        self._model_dir = model_dir

        onnx_file = model_dir / "model.onnx"
        tokenizer_file = model_dir / "tokenizer.json"

        if not onnx_file.exists():
            raise ModelNotInstalledError(f"ONNX model file missing: {onnx_file}")
        if not tokenizer_file.exists():
            raise ModelCorruptError(f"Tokenizer file missing: {tokenizer_file}")

        try:
            import onnxruntime as ort
            from tokenizers import Tokenizer

            # Configure CPU execution
            opts = ort.SessionOptions()
            opts.intra_op_num_threads = settings.WHISPER_CPU_THREADS
            opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL

            self._session = ort.InferenceSession(str(onnx_file), opts, providers=["CPUExecutionProvider"])
            self._tokenizer = Tokenizer.from_file(str(tokenizer_file))
            self._tokenizer.enable_padding(length=512, pad_id=0, pad_token="[PAD]")
            self._tokenizer.enable_truncation(max_length=512)
            logger.info(f"Loaded ONNX embedding engine '{self.model_name}' successfully on CPU.")
        except Exception as e:
            logger.error(f"Failed to load ONNX embedding engine: {e}")
            raise ModelCorruptError(f"Failed to initialize embedding runtime: {e}")

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embeds a list of documents with 'passage: ' prefix."""
        if not texts:
            return []

        self._load_engine()
        prefixed = [t if t.startswith("passage: ") else f"passage: {t}" for t in texts]

        batch_size = settings.EMBEDDING_BATCH_SIZE
        all_embeddings: List[List[float]] = []

        for i in range(0, len(prefixed), batch_size):
            batch = prefixed[i:i + batch_size]
            encodings = self._tokenizer.encode_batch(batch)

            input_ids = np.array([enc.ids for enc in encodings], dtype=np.int64)
            attention_mask = np.array([enc.attention_mask for enc in encodings], dtype=np.int64)

            # Check model input names
            input_names = [inp.name for inp in self._session.get_inputs()]
            ort_inputs = {"input_ids": input_ids, "attention_mask": attention_mask}
            if "token_type_ids" in input_names:
                ort_inputs["token_type_ids"] = np.zeros_like(input_ids)

            outputs = self._session.run(None, ort_inputs)
            # outputs[0] is token_embeddings: shape (batch_size, seq_len, hidden_size)
            token_embeddings = outputs[0]

            # Mean pooling with attention mask
            input_mask_expanded = np.expand_dims(attention_mask, -1).astype(np.float32)
            sum_embeddings = np.sum(token_embeddings * input_mask_expanded, axis=1)
            sum_mask = np.clip(input_mask_expanded.sum(axis=1), a_min=1e-9, a_max=None)
            pooled = sum_embeddings / sum_mask

            # L2 normalization
            norms = np.linalg.norm(pooled, axis=1, keepdims=True)
            norms = np.clip(norms, a_min=1e-9, a_max=None)
            normalized = (pooled / norms).astype(np.float32)

            all_embeddings.extend(normalized.tolist())

        return all_embeddings

    def embed_query(self, query: str) -> List[float]:
        """Embeds a query with 'query: ' prefix."""
        prefixed = query if query.startswith("query: ") else f"query: {query}"
        results = self.embed_documents([prefixed])
        return results[0] if results else [0.0] * self._dimension

    def unload(self):
        """Releases ONNX session to free RAM."""
        self._session = None
        self._tokenizer = None
        import gc
        gc.collect()


class EmbeddingEngineFactory:
    """
    Factory that returns the ONNX embedding engine when installed,
    or MockEmbeddingEngine ONLY when explicitly enabled by automated test fixtures.
    Production startup will NEVER silently fall back to mock embeddings.
    """
    _instance: Optional[BaseEmbeddingEngine] = None
    _force_mock: bool = False

    @classmethod
    def set_force_mock(cls, enabled: bool):
        """Allows test fixtures to isolate embedding generation."""
        cls._force_mock = enabled
        cls._instance = None

    @classmethod
    def is_mock_enabled(cls) -> bool:
        """Returns True if the engine is explicitly running in mock test mode."""
        return cls._force_mock

    @classmethod
    def is_semantic_available(cls) -> bool:
        """
        Returns True only if real model weights are present on disk,
        or if explicitly running in mock test mode.
        """
        if cls._force_mock:
            return True
        model_name = settings.EMBEDDING_DEFAULT_MODEL
        return embedding_model_manager.is_model_installed(model_name)

    @classmethod
    def get_engine(cls) -> BaseEmbeddingEngine:
        """
        Retrieves active embedding engine.
        Raises ModelNotInstalledError if weights are missing in production mode.
        """
        if cls._instance is not None:
            return cls._instance

        model_name = settings.EMBEDDING_DEFAULT_MODEL

        # Automated test fixture mode
        if cls._force_mock:
            logger.info("Using MockEmbeddingEngine (explicitly enabled by automated test fixture).")
            cls._instance = MockEmbeddingEngine(dimension=settings.EMBEDDING_DIMENSION)
            return cls._instance

        # Production / Normal mode: strict enforcement of real model weights
        if not embedding_model_manager.is_model_installed(model_name):
            raise ModelNotInstalledError(
                f"Embedding model '{model_name}' is not installed locally. "
                "Semantic vector indexing and search are disabled. "
                "Production mode strictly forbids mock embedding fallback. "
                "Please download model weights via Settings or the CLI."
            )

        cls._instance = ONNXEmbeddingEngine(model_name=model_name)
        return cls._instance


embedding_engine = EmbeddingEngineFactory

