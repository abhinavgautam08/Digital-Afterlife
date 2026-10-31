"""
Pydantic schemas for AI / Ollama status and model discovery.
"""
from typing import List, Optional
from pydantic import BaseModel


class ModelInfo(BaseModel):
    name: str
    model: str
    size: Optional[int] = None
    modified_at: Optional[str] = None
    is_configured: bool = False


class AIStatusResponse(BaseModel):
    status: str  # "online" | "offline"
    ollama_running: bool
    configured_model: str
    model_available: bool
    base_url: str
    installed_models: List[str] = []
    message: str
    setup_instructions: Optional[str] = None


class AIModelsResponse(BaseModel):
    models: List[ModelInfo]
    count: int
    configured_model: str

