"""
AI Studio routes.
Provides health, local model availability, and setup guidance for Ollama.
"""
from fastapi import APIRouter
from backend.app.schemas.ai import AIStatusResponse, AIModelsResponse
from backend.app.services.ai_service import ai_service

router = APIRouter(prefix="/ai", tags=["AI Studio"])


@router.get("/status", response_model=AIStatusResponse)
def get_ai_status():
    """Checks whether local Ollama is active and if the configured model is installed."""
    return ai_service.check_status()


@router.get("/models", response_model=AIModelsResponse)
def get_available_models():
    """Enumerates locally installed models from the offline Ollama instance."""
    return ai_service.list_models()

