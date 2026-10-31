"""
System monitoring and statistics aggregation service.
Computes real statistics from SQLite database and local disk storage.
No mock or placeholder data.
"""
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.app.core.config import settings
from backend.app.models.memory import Memory
from backend.app.models.person import Person
from backend.app.services.storage_service import storage_service
from backend.app.services.ai_service import ai_service
from backend.app.schemas.system import (
    SystemStatusResponse,
    StorageStatus,
    MemoryStats,
    HealthResponse
)


class SystemService:
    @staticmethod
    def get_system_status(db: Session) -> SystemStatusResponse:
        """Calculates accurate live metrics directly from SQLite database and local storage."""
        total_memories = db.query(Memory).count()
        photographs = db.query(Memory).filter(Memory.memory_type == "photograph").count()
        audio_recordings = db.query(Memory).filter(Memory.memory_type == "audio").count()
        documents = db.query(Memory).filter(Memory.memory_type == "document").count()
        stories = db.query(Memory).filter(Memory.memory_type == "story").count()
        videos = db.query(Memory).filter(Memory.memory_type == "video").count()
        total_people = db.query(Person).count()

        storage_data = storage_service.get_storage_stats()
        ai_stat = ai_service.check_status()

        return SystemStatusResponse(
            application_name=settings.APP_NAME,
            version=settings.VERSION,
            environment=settings.ENVIRONMENT,
            privacy_mode="Strict Offline-First (No External Telemetry)",
            database_connected=True,
            ai_status=ai_stat.status,
            storage=StorageStatus(
                storage_directory=storage_data["storage_directory"],
                total_files=storage_data["total_files"],
                total_bytes=storage_data["total_bytes"],
                formatted_size=storage_data["formatted_size"]
            ),
            statistics=MemoryStats(
                total_memories=total_memories,
                photographs=photographs,
                audio_recordings=audio_recordings,
                documents=documents,
                stories=stories,
                videos=videos,
                total_people=total_people
            )
        )

    @staticmethod
    def get_health() -> HealthResponse:
        """Lightweight health probe."""
        ai_stat = ai_service.check_status()
        return HealthResponse(
            status="healthy",
            app=settings.APP_NAME,
            version=settings.VERSION,
            database="connected",
            ai_service=ai_stat.status
        )


system_service = SystemService()

