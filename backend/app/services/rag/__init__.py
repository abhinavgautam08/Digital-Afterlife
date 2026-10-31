"""
RAG and Semantic Search Subsystem for Digital Afterlife.
Export key interfaces: chunker, embedding_engine, vector_store, indexing_service, retrieval_service, rag_service.
"""
from backend.app.services.rag.chunker import chunker, MemoryChunk
from backend.app.services.rag.embedding_engine import (
    embedding_engine,
    BaseEmbeddingEngine,
    ONNXEmbeddingEngine,
    MockEmbeddingEngine
)
from backend.app.services.rag.model_manager import (
    embedding_model_manager,
    ModelNotInstalledError,
    ModelCorruptError
)
from backend.app.services.rag.vector_store import vector_store
from backend.app.services.rag.indexing_service import indexing_service
from backend.app.services.rag.retrieval_service import retrieval_service
from backend.app.services.rag.rag_service import rag_service, RAGResponse, CitationItem

__all__ = [
    "chunker",
    "MemoryChunk",
    "embedding_engine",
    "BaseEmbeddingEngine",
    "ONNXEmbeddingEngine",
    "MockEmbeddingEngine",
    "embedding_model_manager",
    "ModelNotInstalledError",
    "ModelCorruptError",
    "vector_store",
    "indexing_service",
    "retrieval_service",
    "rag_service",
    "RAGResponse",
    "CitationItem",
]

