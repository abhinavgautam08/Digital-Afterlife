"""
Pydantic schemas for System Status and Health checks.
"""
from typing import Dict, Any
from pydantic import BaseModel


class StorageStatus(BaseModel):
    storage_directory: str
    total_files: int
    total_bytes: int
    formatted_size: str


class MemoryStats(BaseModel):
    total_memories: int
    photographs: int
    audio_recordings: int
    documents: int
    stories: int
    videos: int
    total_people: int


class SystemStatusResponse(BaseModel):
    application_name: str
    version: str
    environment: str
    privacy_mode: str
    database_connected: bool
    ai_status: str
    storage: StorageStatus
    statistics: MemoryStats


class HealthResponse(BaseModel):
    status: str
    app: str
    version: str
    database: str
    ai_service: str

