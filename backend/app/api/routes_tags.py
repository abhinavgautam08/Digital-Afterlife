"""
Tag management API routes for Phase 2.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.database.session import get_db
from backend.app.schemas.tag import TagCreate, TagUpdate, TagRead
from backend.app.services.tag_service import tag_service

router = APIRouter(prefix="/tags", tags=["Tags"])


@router.get("", response_model=List[TagRead])
def list_tags(db: Session = Depends(get_db)):
    """Retrieves all heritage categorization tags."""
    return tag_service.list_tags(db)


@router.post("", response_model=TagRead, status_code=status.HTTP_201_CREATED)
def create_tag(tag_in: TagCreate, db: Session = Depends(get_db)):
    """Creates a new categorization tag."""
    tag = tag_service.create_tag(db, tag_in)
    return TagRead(
        id=tag.id,
        name=tag.name,
        created_at=tag.created_at,
        memories_count=0
    )


@router.patch("/{tag_id}", response_model=TagRead)
def update_tag(tag_id: str, tag_update: TagUpdate, db: Session = Depends(get_db)):
    """Renames an existing tag."""
    tag = tag_service.update_tag(db, tag_id, tag_update)
    if not tag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found.")
    return TagRead(
        id=tag.id,
        name=tag.name,
        created_at=tag.created_at,
        memories_count=0
    )


@router.delete("/{tag_id}", status_code=status.HTTP_200_OK)
def delete_tag(tag_id: str, db: Session = Depends(get_db)):
    """Deletes a tag and removes associations."""
    success = tag_service.delete_tag(db, tag_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found.")
    return {"status": "success", "message": f"Tag {tag_id} deleted."}

