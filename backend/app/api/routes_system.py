"""
System status and diagnostics routes.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.database.session import get_db
from backend.app.schemas.system import SystemStatusResponse
from backend.app.services.system_service import system_service

router = APIRouter(prefix="/system", tags=["System"])


@router.get("/status", response_model=SystemStatusResponse)
def get_system_status(db: Session = Depends(get_db)):
    """Provides comprehensive live storage and memory metrics computed from SQLite."""
    return system_service.get_system_status(db)

