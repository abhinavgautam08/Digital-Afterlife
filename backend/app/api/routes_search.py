"""
Search and RAG API routes for Digital Afterlife.
Endpoints for semantic retrieval, hybrid search, question answering with citations,
vector store lifecycle management, and embedding models.
"""
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, status
from sqlalchemy.orm import Session

from backend.app.database.session import get_db
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.models.indexing_job import IndexingJob
from backend.app.schemas.search import (
    SearchQueryRequest,
    SearchResponse,
    SearchResultItem,
    AskMemoriesRequest,
    AskMemoriesResponse,
    IndexStatusResponse,
    ModelDownloadRequest,
)
from backend.app.services.rag.retrieval_service import retrieval_service
from backend.app.services.rag.rag_service import rag_service
from backend.app.services.rag.indexing_service import indexing_service
from backend.app.services.rag.vector_store import vector_store
from backend.app.services.rag.model_manager import embedding_model_manager
from backend.app.services.rag.embedding_engine import embedding_engine
from backend.app.core.crypto import vault_key_manager

router = APIRouter(tags=["Search & RAG"])


def _check_vault_unlocked():
    """Ensures search and RAG operations reject access while vault is locked."""
    if vault_key_manager.is_initialized() and not vault_key_manager.is_unlocked():
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="Vault is locked. Unlock the vault with your passphrase to query memories."
        )


@router.post("/search/semantic", response_model=SearchResponse)
def semantic_search(
    req: SearchQueryRequest,
    db: Session = Depends(get_db)
):
    """Executes semantic similarity search over indexed memory chunks."""
    _check_vault_unlocked()
    semantic_avail = embedding_engine.is_semantic_available()
    results = retrieval_service.semantic_search(
        db=db,
        query=req.query,
        top_k=req.top_k,
        date_from=req.date_from,
        date_to=req.date_to,
        person_id=req.person_id,
        memory_type=req.memory_type,
        tags=req.tags,
        transcript_language=req.transcript_language,
    )
    items = [
        SearchResultItem(
            chunk_id=r.get("chunk_id", ""),
            memory_id=r.get("memory_id", ""),
            memory_title=r.get("memory_title", "Untitled"),
            memory_type=r.get("memory_type", "document"),
            memory_date=r.get("memory_date"),
            source_type=r.get("source_type", "document"),
            original_filename=r.get("original_filename", ""),
            text=r.get("text", ""),
            similarity=r.get("similarity", 0.0),
            start_time=r.get("start_time"),
            end_time=r.get("end_time"),
            speaker_label=r.get("speaker_label"),
            tags=r.get("tags", []),
            person_ids=r.get("person_ids", []),
        )
        for r in results
    ]
    warning = None if semantic_avail else f"Semantic model '{settings.EMBEDDING_DEFAULT_MODEL}' is uninstalled. Zero vector results returned."
    return SearchResponse(
        query=req.query,
        mode="semantic",
        total_results=len(items),
        results=items,
        semantic_available=semantic_avail,
        fallback_mode="real_semantic" if semantic_avail else "keyword_only",
        warning=warning
    )


@router.post("/search/hybrid", response_model=SearchResponse)
def hybrid_search(
    req: SearchQueryRequest,
    db: Session = Depends(get_db)
):
    """Executes hybrid retrieval combining semantic similarity and keyword matching via RRF."""
    _check_vault_unlocked()
    semantic_avail = embedding_engine.is_semantic_available()
    results = retrieval_service.hybrid_search(
        db=db,
        query=req.query,
        top_k=req.top_k,
        date_from=req.date_from,
        date_to=req.date_to,
        person_id=req.person_id,
        memory_type=req.memory_type,
        tags=req.tags,
        transcript_language=req.transcript_language,
    )
    items = [
        SearchResultItem(
            chunk_id=r.get("chunk_id", ""),
            memory_id=r.get("memory_id", ""),
            memory_title=r.get("memory_title", "Untitled"),
            memory_type=r.get("memory_type", "document"),
            memory_date=r.get("memory_date"),
            source_type=r.get("source_type", "document"),
            original_filename=r.get("original_filename", ""),
            text=r.get("text", ""),
            similarity=r.get("similarity", 0.0),
            start_time=r.get("start_time"),
            end_time=r.get("end_time"),
            speaker_label=r.get("speaker_label"),
            tags=r.get("tags", []),
            person_ids=r.get("person_ids", []),
        )
        for r in results
    ]
    warning = None if semantic_avail else "Semantic model not installed. Fallback to SQLite keyword matching only."
    return SearchResponse(
        query=req.query,
        mode="hybrid",
        total_results=len(items),
        results=items,
        semantic_available=semantic_avail,
        fallback_mode="real_semantic" if semantic_avail else "keyword_only",
        warning=warning
    )


@router.post("/memories/ask", response_model=AskMemoriesResponse)
def ask_memories(
    req: AskMemoriesRequest,
    db: Session = Depends(get_db)
):
    """
    Asks a natural language question about family memories.
    Uses local semantic/hybrid retrieval and local Ollama inference.
    Returns grounded answer with structured, verified source citations.
    """
    _check_vault_unlocked()
    res = rag_service.ask_memories(
        db=db,
        query=req.query,
        retrieval_mode=req.retrieval_mode,
        top_k=req.top_k,
        date_from=req.date_from,
        date_to=req.date_to,
        person_id=req.person_id,
        memory_type=req.memory_type,
        tags=req.tags,
        transcript_language=req.transcript_language,
    )
    return AskMemoriesResponse(
        answer=res.answer,
        evidence_status=res.evidence_status,
        citations=[
            {
                "index": c.index,
                "memory_id": c.memory_id,
                "title": c.title,
                "source_type": c.source_type,
                "memory_type": c.memory_type,
                "original_filename": c.original_filename,
                "excerpt": c.excerpt,
                "start_time": c.start_time,
                "end_time": c.end_time,
                "speaker_label": c.speaker_label,
                "event_date": c.event_date,
                "similarity": c.similarity,
            }
            for c in res.citations
        ],
        query=res.query,
        retrieval_mode=res.retrieval_mode,
        sources_retrieved_count=res.sources_retrieved_count,
        model_name=res.model_name,
        processing_time_seconds=res.processing_time_seconds,
        semantic_available=res.semantic_available,
        fallback_mode=res.fallback_mode,
        warning=res.warning
    )


@router.get("/search/index/status", response_model=IndexStatusResponse)
def get_index_status(db: Session = Depends(get_db)):
    """Reports synchronization status between SQLite and ChromaDB vector store."""
    status_data = indexing_service.get_index_status(db)
    return IndexStatusResponse(**status_data)


@router.post("/search/index/rebuild")
def rebuild_index(db: Session = Depends(get_db)):
    """Rebuilds the entire vector index from authoritative SQLite records."""
    _check_vault_unlocked()
    report = indexing_service.rebuild_index(db)
    return report


@router.post("/search/index/retry")
def retry_failed_indexing(db: Session = Depends(get_db)):
    """Retries any indexing jobs that previously failed."""
    _check_vault_unlocked()
    return indexing_service.retry_failed_jobs(db)


@router.get("/search/index/jobs")
def list_indexing_jobs(
    status: Optional[str] = Query(None, description="Filter by job status"),
    db: Session = Depends(get_db)
):
    """Lists indexing job status records from SQLite."""
    q = db.query(IndexingJob)
    if status:
        q = q.filter(IndexingJob.status == status.lower())
    jobs = q.order_by(IndexingJob.updated_at.desc()).limit(100).all()
    return [
        {
            "id": j.id,
            "memory_id": j.memory_id,
            "status": j.status,
            "chunk_count": j.chunk_count,
            "content_hash": j.content_hash,
            "error_message": j.error_message,
            "created_at": j.created_at.isoformat(),
            "updated_at": j.updated_at.isoformat(),
        }
        for j in jobs
    ]


@router.get("/search/models")
def list_embedding_models():
    """Lists supported local embedding models with installation status."""
    return embedding_model_manager.list_models()


@router.post("/search/models/download")
def download_embedding_model(
    req: ModelDownloadRequest,
    background_tasks: BackgroundTasks
):
    """Explicitly triggers downloading embedding model weights."""
    clean_name = req.model_name.strip().lower()
    if clean_name not in embedding_model_manager.SUPPORTED_MODELS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported model '{req.model_name}'."
        )

    # Trigger download
    try:
        embedding_model_manager.download_model(clean_name)
        return {"status": "completed", "model_name": clean_name, "message": "Model downloaded successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")


@router.get("/search/status")
def search_system_status(db: Session = Depends(get_db)):
    """Unified search and RAG health check."""
    idx_status = indexing_service.get_index_status(db)
    return {
        "status": "online",
        "semantic_available": idx_status["semantic_available"],
        "keyword_available": idx_status["keyword_available"],
        "vector_store_available": idx_status["vector_store_available"],
        "embedding_model_name": idx_status["embedding_model_name"],
        "embedding_model_loaded": idx_status["embedding_model_loaded"],
        "fallback_mode": idx_status["fallback_mode"],
        "vector_store": idx_status["vector_store"],
        "embedding_model": idx_status["embedding_model"],
        "total_memories": idx_status["total_memories"],
        "indexed_memories": idx_status["indexed_memories"],
        "is_synchronized": idx_status["is_synchronized"],
        "ollama_model": settings.OLLAMA_MODEL,
    }

