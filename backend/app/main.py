"""
Main FastAPI entry point for Digital Afterlife - Memory Keeper.
Phase 1: Local-first, privacy-focused foundation.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.database.session import init_db
from backend.app.api import api_router
from backend.app.services.speech.job_worker import transcription_worker


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure tables and data directories exist
    logger.info(f"Starting {settings.APP_NAME} v{settings.VERSION}")
    logger.info(f"Local storage path: {settings.STORAGE_DIR}")
    init_db()
    transcription_worker.start()
    yield
    # Shutdown
    transcription_worker.stop()
    logger.info("Shutting down application cleanly.")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="Offline-first, privacy-respecting personal and family memory preservation platform.",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Strict local CORS policy
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Register API routes
app.include_router(api_router)


@app.get("/", tags=["Root"])
def root():
    return {
        "app": settings.APP_NAME,
        "version": settings.VERSION,
        "philosophy": "Your memories. Your machine. Your legacy.",
        "privacy": "Local-only. Zero external telemetry.",
        "documentation": "/api/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )

