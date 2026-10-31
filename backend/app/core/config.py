"""
Application configuration for Digital Afterlife - Memory Keeper.
Phase 2: Local-first, privacy-respecting configuration with multimedia preservation support.
"""
from pathlib import Path
from typing import List, Set
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Digital Afterlife – Memory Keeper"
    VERSION: str = "0.2.0"
    ENVIRONMENT: str = "production"
    DEBUG: bool = False

    # Network binding - strictly bound to localhost by default
    HOST: str = "127.0.0.1"
    PORT: int = 8000

    # Paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    STORAGE_DIR: Path = BASE_DIR / "data" / "memories"
    THUMBNAILS_DIR: Path = BASE_DIR / "data" / "thumbnails"
    CACHE_DIR: Path = BASE_DIR / "data" / "cache"
    DATABASE_PATH: Path = BASE_DIR / "data" / "digital_afterlife.db"

    # Category Subdirectories
    IMAGES_DIR: Path = STORAGE_DIR / "images"
    AUDIO_DIR: Path = STORAGE_DIR / "audio"
    VIDEO_DIR: Path = STORAGE_DIR / "video"
    DOCUMENTS_DIR: Path = STORAGE_DIR / "documents"
    STORIES_DIR: Path = STORAGE_DIR / "stories"
    WHISPER_MODELS_DIR: Path = BASE_DIR / "models" / "whisper"
    EMBEDDING_MODELS_DIR: Path = BASE_DIR / "models" / "embeddings"
    VECTOR_STORE_DIR: Path = BASE_DIR / "data" / "vector_store"

    # Database
    DATABASE_URL: str = f"sqlite:///{DATABASE_PATH.as_posix()}"

    # File uploads - 100 MB max limit
    MAX_UPLOAD_SIZE_BYTES: int = 100 * 1024 * 1024  # 100 MB max

    # Supported Phase 2 Extensions
    ALLOWED_EXTENSIONS: Set[str] = {
        # Images
        ".jpg", ".jpeg", ".png", ".webp", ".gif",
        # Audio
        ".mp3", ".wav", ".m4a", ".ogg", ".flac",
        # Video
        ".mp4", ".webm", ".mov",
        # Documents
        ".pdf", ".txt", ".md", ".docx"
    }

    # Whitelisted MIME Types
    ALLOWED_MIME_TYPES: Set[str] = {
        # Images
        "image/jpeg", "image/png", "image/webp", "image/gif",
        # Audio
        "audio/mpeg", "audio/wav", "audio/x-wav", "audio/x-m4a", "audio/mp4",
        "audio/m4a", "audio/ogg", "audio/flac", "audio/x-flac",
        # Video
        "video/mp4", "video/webm", "video/quicktime",
        # Documents
        "application/pdf", "text/plain", "text/markdown",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword", "application/octet-stream"
    }

    # Ollama Local AI
    OLLAMA_BASE_URL: str = "http://127.0.0.1:11434"
    OLLAMA_MODEL: str = "qwen2.5:3b"
    OLLAMA_TIMEOUT_SECONDS: float = 3.0

    # Local Speech-to-Text (Whisper / faster-whisper)
    WHISPER_DEFAULT_MODEL: str = "base"
    WHISPER_DEVICE: str = "cpu"
    WHISPER_COMPUTE_TYPE: str = "int8"
    WHISPER_CPU_THREADS: int = 4
    WHISPER_QUEUE_CONCURRENCY: int = 1
    AUTO_DOWNLOAD_MODELS: bool = False  # Privacy safeguard: Never download silently

    # Local Semantic Search & RAG (Phase 4)
    EMBEDDING_DEFAULT_MODEL: str = "multilingual-e5-small"
    EMBEDDING_DIMENSION: int = 384
    EMBEDDING_BATCH_SIZE: int = 16
    RAG_CHUNK_SIZE_TOKENS: int = 500
    RAG_CHUNK_OVERLAP_TOKENS: int = 60
    RAG_TOP_K: int = 5
    RAG_SIMILARITY_THRESHOLD: float = 0.55
    RAG_MAX_CONTEXT_TOKENS: int = 2000
    RAG_TEMPERATURE: float = 0.1

    # Encryption abstraction preparation (Phase 1/2 interface)
    ENCRYPTION_ENABLED: bool = False
    ENCRYPTION_KEY: str = ""

    # CORS settings
    CORS_ORIGINS: List[str] = [
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://localhost:3000",
        "http://127.0.0.1:8000",
    ]

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore"
    }


settings = Settings()

# Ensure directories exist
for directory in [
    settings.DATA_DIR,
    settings.STORAGE_DIR,
    settings.THUMBNAILS_DIR,
    settings.CACHE_DIR,
    settings.IMAGES_DIR,
    settings.AUDIO_DIR,
    settings.VIDEO_DIR,
    settings.DOCUMENTS_DIR,
    settings.STORIES_DIR,
    settings.WHISPER_MODELS_DIR,
    settings.EMBEDDING_MODELS_DIR,
    settings.VECTOR_STORE_DIR,
]:
    directory.mkdir(parents=True, exist_ok=True)
