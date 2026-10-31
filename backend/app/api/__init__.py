"""
API routes module aggregator.
Phase 3: Includes health, system, memories, people, tags, ai, transcription, and transcripts routes.
"""
from fastapi import APIRouter

from backend.app.api.routes_health import router as health_router
from backend.app.api.routes_system import router as system_router
from backend.app.api.routes_memories import router as memories_router
from backend.app.api.routes_people import router as people_router
from backend.app.api.routes_tags import router as tags_router
from backend.app.api.routes_ai import router as ai_router
from backend.app.api.routes_transcription import router as transcription_router
from backend.app.api.routes_transcripts import router as transcripts_router
from backend.app.api.routes_search import router as search_router
from backend.app.api.routes_storytelling import router as storytelling_router
from backend.app.api.routes_security import router as security_router

api_router = APIRouter(prefix="/api")
api_router.include_router(health_router)
api_router.include_router(system_router)
api_router.include_router(memories_router)
api_router.include_router(people_router)
api_router.include_router(tags_router)
api_router.include_router(ai_router)
api_router.include_router(transcription_router)
api_router.include_router(transcripts_router)
api_router.include_router(search_router)
api_router.include_router(storytelling_router)
api_router.include_router(security_router)

__all__ = ["api_router"]
