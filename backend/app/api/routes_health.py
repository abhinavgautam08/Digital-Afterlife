"""
Health check route.
"""
from fastapi import APIRouter
from backend.app.schemas.system import HealthResponse
from backend.app.services.system_service import system_service

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
def health_check():
    """Returns application health and subsystem connectivity status."""
    return system_service.get_health()

