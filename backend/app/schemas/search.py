"""
Search and RAG Pydantic schemas.
"""
from typing import List, Optional, Any, Dict
from datetime import datetime
from pydantic import BaseModel, Field


class SearchQueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000, description="Search terms or semantic question")
    top_k: int = Field(default=5, ge=1, le=50)
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    person_id: Optional[str] = None
    memory_type: Optional[str] = None
    tags: Optional[List[str]] = None
    transcript_language: Optional[str] = None


class SearchResultItem(BaseModel):
    chunk_id: str
    memory_id: str
    memory_title: str
    memory_type: str
    memory_date: Optional[str] = None
    source_type: str
    original_filename: str
    text: str
    similarity: float = 0.0
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    speaker_label: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    person_ids: List[str] = Field(default_factory=list)


class SearchResponse(BaseModel):
    query: str
    mode: str
    total_results: int
    results: List[SearchResultItem]
    semantic_available: bool = True
    fallback_mode: str = "real_semantic"  # "real_semantic" | "keyword_only"
    warning: Optional[str] = None


class AskMemoriesRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000, description="Natural language question about memories")
    retrieval_mode: str = Field(default="hybrid", description="'hybrid' or 'semantic'")
    top_k: int = Field(default=5, ge=1, le=20)
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    person_id: Optional[str] = None
    memory_type: Optional[str] = None
    tags: Optional[List[str]] = None
    transcript_language: Optional[str] = None


class CitationItemSchema(BaseModel):
    index: int
    memory_id: str
    title: str
    source_type: str
    memory_type: str
    original_filename: str
    excerpt: str
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    speaker_label: Optional[str] = None
    event_date: Optional[str] = None
    similarity: float = 0.0


class AskMemoriesResponse(BaseModel):
    answer: str
    evidence_status: str
    citations: List[CitationItemSchema]
    query: str
    retrieval_mode: str
    sources_retrieved_count: int
    model_name: str
    processing_time_seconds: float
    semantic_available: bool = True
    fallback_mode: str = "real_semantic"  # "real_semantic" | "keyword_only"
    warning: Optional[str] = None


class IndexStatusResponse(BaseModel):
    total_memories: int
    indexed_memories: int
    failed_jobs: int
    pending_jobs: int
    vector_store: Dict[str, Any]
    embedding_model: Dict[str, Any]
    is_synchronized: bool
    semantic_available: bool = False
    keyword_available: bool = True
    vector_store_available: bool = False
    embedding_model_name: str = "multilingual-e5-small"
    embedding_model_loaded: bool = False
    fallback_mode: str = "keyword_only"  # "real_semantic" | "keyword_only"


class ModelDownloadRequest(BaseModel):
    model_name: str = Field(default="multilingual-e5-small")

