"""
Storytelling and Memory Preservation API Routes.
Phase 5: Grounded Biographies, Life Timelines, Memory Stories, Collections, and Remembrance Pages.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.database.session import get_db
from backend.app.core.logging import logger
from backend.app.schemas.storytelling import (
    BiographyGenerateRequest,
    StoryGenerateRequest,
    TimelineGenerateRequest,
    TimelineEventCreate,
    TimelineEventUpdate,
    TimelineEventResponse,
    StoryArtifactUpdate,
    StoryArtifactResponse,
    RemembrancePageUpdate,
    RemembrancePageResponse,
    CollectionCreate,
    CollectionUpdate,
    CollectionItemAdd,
    CollectionResponse,
)
from backend.app.services.storytelling_service import (
    storytelling_service,
    StorytellingError,
    PersonNotFoundError,
    CrossPersonMemoryError,
    InsufficientEvidenceError,
    ModelUnavailableError,
)

from backend.app.core.crypto import vault_key_manager

router = APIRouter(prefix="/storytelling", tags=["Storytelling & Remembrance"])


def _check_vault_unlocked():
    """Ensures storytelling operations reject access while vault is locked."""
    if vault_key_manager.is_initialized() and not vault_key_manager.is_unlocked():
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="Vault is locked. Unlock the vault with your passphrase to access storytelling features."
        )


# -----------------------------------------------------------------------------
# Biographies & Stories Generation
# -----------------------------------------------------------------------------

@router.post("/biographies/generate", response_model=StoryArtifactResponse)
def generate_biography(req: BiographyGenerateRequest, db: Session = Depends(get_db)):
    """Generates an evidence-grounded biography for a selected person."""
    _check_vault_unlocked()
    try:
        return storytelling_service.generate_biography(db, req)
    except PersonNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except CrossPersonMemoryError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except ModelUnavailableError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
    except StorytellingError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/stories/generate", response_model=StoryArtifactResponse)
def generate_story(req: StoryGenerateRequest, db: Session = Depends(get_db)):
    """Generates a cohesive story grounded in selected memories."""
    _check_vault_unlocked()
    try:
        return storytelling_service.generate_story(db, req)
    except PersonNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except CrossPersonMemoryError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except InsufficientEvidenceError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except ModelUnavailableError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
    except StorytellingError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# -----------------------------------------------------------------------------
# Life Timelines
# -----------------------------------------------------------------------------

@router.post("/timelines/generate", response_model=List[TimelineEventResponse])
def generate_timeline(req: TimelineGenerateRequest, db: Session = Depends(get_db)):
    """Extracts chronological milestone events from documented memories."""
    _check_vault_unlocked()
    try:
        return storytelling_service.generate_timeline(db, req)
    except PersonNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except CrossPersonMemoryError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/timelines/person/{person_id}", response_model=List[TimelineEventResponse])
def get_person_timeline(person_id: str, db: Session = Depends(get_db)):
    """Retrieves all timeline events for a person."""
    _check_vault_unlocked()
    try:
        return storytelling_service.get_person_timeline(db, person_id)
    except PersonNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/timelines/events", response_model=TimelineEventResponse)
def create_timeline_event(data: TimelineEventCreate, db: Session = Depends(get_db)):
    """Manually creates a timeline event."""
    _check_vault_unlocked()
    try:
        return storytelling_service.create_timeline_event(db, data)
    except PersonNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except CrossPersonMemoryError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.patch("/timelines/events/{event_id}", response_model=TimelineEventResponse)
def update_timeline_event(event_id: str, data: TimelineEventUpdate, db: Session = Depends(get_db)):
    """Updates a timeline event (title, date, description, verification status)."""
    _check_vault_unlocked()
    try:
        return storytelling_service.update_timeline_event(db, event_id, data)
    except CrossPersonMemoryError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except StorytellingError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.delete("/timelines/events/{event_id}")
def delete_timeline_event(event_id: str, db: Session = Depends(get_db)):
    """Deletes a timeline event."""
    _check_vault_unlocked()
    try:
        storytelling_service.delete_timeline_event(db, event_id)
        return {"message": "Timeline event deleted successfully.", "id": event_id}
    except StorytellingError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# -----------------------------------------------------------------------------
# Story Artifacts CRUD & Approval
# -----------------------------------------------------------------------------

@router.get("/artifacts/{artifact_id}", response_model=StoryArtifactResponse)
def get_artifact(artifact_id: str, db: Session = Depends(get_db)):
    """Retrieves a single artifact with its sources."""
    _check_vault_unlocked()
    try:
        return storytelling_service.get_artifact(db, artifact_id)
    except StorytellingError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.patch("/artifacts/{artifact_id}", response_model=StoryArtifactResponse)
def update_artifact(artifact_id: str, data: StoryArtifactUpdate, db: Session = Depends(get_db)):
    """Updates artifact content, title, or approval status."""
    _check_vault_unlocked()
    try:
        return storytelling_service.update_artifact(db, artifact_id, data)
    except StorytellingError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.delete("/artifacts/{artifact_id}")
def delete_artifact(artifact_id: str, db: Session = Depends(get_db)):
    """Deletes an artifact without modifying any original memory records."""
    _check_vault_unlocked()
    try:
        storytelling_service.delete_artifact(db, artifact_id)
        return {"message": "Artifact deleted successfully.", "id": artifact_id}
    except StorytellingError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/artifacts/person/{person_id}", response_model=List[StoryArtifactResponse])
def list_person_artifacts(person_id: str, db: Session = Depends(get_db)):
    """Lists all artifacts generated for a person."""
    _check_vault_unlocked()
    try:
        return storytelling_service.list_person_artifacts(db, person_id)
    except PersonNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# -----------------------------------------------------------------------------
# Remembrance Pages (Private Local Only)
# -----------------------------------------------------------------------------

@router.get("/remembrance/{person_id}", response_model=RemembrancePageResponse)
def get_remembrance_page(person_id: str, db: Session = Depends(get_db)):
    """Retrieves or initializes the private remembrance page for a person."""
    _check_vault_unlocked()
    try:
        return storytelling_service.get_or_create_remembrance_page(db, person_id)
    except PersonNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.patch("/remembrance/{person_id}", response_model=RemembrancePageResponse)
def update_remembrance_page(person_id: str, data: RemembrancePageUpdate, db: Session = Depends(get_db)):
    """Updates details on a private remembrance page."""
    _check_vault_unlocked()
    try:
        return storytelling_service.update_remembrance_page(db, person_id, data)
    except PersonNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except CrossPersonMemoryError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except StorytellingError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# -----------------------------------------------------------------------------
# Memory Collections
# -----------------------------------------------------------------------------

@router.get("/collections", response_model=List[CollectionResponse])
def list_collections(person_id: Optional[str] = None, db: Session = Depends(get_db)):
    """Lists collections, optionally filtered by person."""
    _check_vault_unlocked()
    try:
        return storytelling_service.list_collections(db, person_id)
    except PersonNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/collections", response_model=CollectionResponse, status_code=status.HTTP_201_CREATED)
def create_collection(data: CollectionCreate, db: Session = Depends(get_db)):
    """Creates a new thematic memory collection."""
    _check_vault_unlocked()
    try:
        return storytelling_service.create_collection(db, data)
    except PersonNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/collections/{collection_id}", response_model=CollectionResponse)
def get_collection(collection_id: str, db: Session = Depends(get_db)):
    """Retrieves a single collection with its referenced items."""
    _check_vault_unlocked()
    try:
        return storytelling_service.get_collection(db, collection_id)
    except StorytellingError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.patch("/collections/{collection_id}", response_model=CollectionResponse)
def update_collection(collection_id: str, data: CollectionUpdate, db: Session = Depends(get_db)):
    """Updates collection metadata."""
    _check_vault_unlocked()
    try:
        return storytelling_service.update_collection(db, collection_id, data)
    except StorytellingError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.delete("/collections/{collection_id}")
def delete_collection(collection_id: str, db: Session = Depends(get_db)):
    """Deletes a collection without modifying any referenced memories."""
    _check_vault_unlocked()
    try:
        storytelling_service.delete_collection(db, collection_id)
        return {"message": "Collection deleted successfully.", "id": collection_id}
    except StorytellingError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/collections/{collection_id}/items", response_model=CollectionResponse)
def add_collection_item(collection_id: str, data: CollectionItemAdd, db: Session = Depends(get_db)):
    """Adds a memory to a collection."""
    _check_vault_unlocked()
    try:
        return storytelling_service.add_collection_item(db, collection_id, data)
    except StorytellingError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.delete("/collections/{collection_id}/items/{memory_id}", response_model=CollectionResponse)
def remove_collection_item(collection_id: str, memory_id: str, db: Session = Depends(get_db)):
    """Removes a memory from a collection."""
    _check_vault_unlocked()
    try:
        return storytelling_service.remove_collection_item(db, collection_id, memory_id)
    except StorytellingError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

