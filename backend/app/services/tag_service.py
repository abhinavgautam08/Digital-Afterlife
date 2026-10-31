"""
Tag management domain service for Phase 2.
"""
from typing import List, Optional
import uuid
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.app.models.tag import MemoryTag
from backend.app.models.memory import MemoryTagAssociation
from backend.app.schemas.tag import TagCreate, TagUpdate, TagRead


class TagService:
    @staticmethod
    def list_tags(db: Session) -> List[TagRead]:
        """Lists all tags with their associated memory counts."""
        tags = db.query(MemoryTag).order_by(MemoryTag.name.asc()).all()
        results = []
        for tag in tags:
            count = db.query(MemoryTagAssociation).filter(MemoryTagAssociation.tag_id == tag.id).count()
            results.append(
                TagRead(
                    id=tag.id,
                    name=tag.name,
                    created_at=tag.created_at,
                    memories_count=count
                )
            )
        return results

    @staticmethod
    def get_tag_by_id(db: Session, tag_id: str) -> Optional[MemoryTag]:
        return db.query(MemoryTag).filter(MemoryTag.id == tag_id).first()

    @staticmethod
    def get_tag_by_name(db: Session, name: str) -> Optional[MemoryTag]:
        return db.query(MemoryTag).filter(MemoryTag.name == name.strip().lower()).first()

    @staticmethod
    def create_tag(db: Session, tag_in: TagCreate) -> MemoryTag:
        clean_name = tag_in.name.strip().lower()
        existing = db.query(MemoryTag).filter(MemoryTag.name == clean_name).first()
        if existing:
            return existing

        tag = MemoryTag(
            id=str(uuid.uuid4()),
            name=clean_name
        )
        db.add(tag)
        db.commit()
        db.refresh(tag)
        return tag

    @staticmethod
    def update_tag(db: Session, tag_id: str, tag_update: TagUpdate) -> Optional[MemoryTag]:
        tag = db.query(MemoryTag).filter(MemoryTag.id == tag_id).first()
        if not tag:
            return None

        tag.name = tag_update.name.strip().lower()
        db.commit()
        db.refresh(tag)
        return tag

    @staticmethod
    def delete_tag(db: Session, tag_id: str) -> bool:
        tag = db.query(MemoryTag).filter(MemoryTag.id == tag_id).first()
        if not tag:
            return False

        # Associations will cascade or can be cleared
        db.query(MemoryTagAssociation).filter(MemoryTagAssociation.tag_id == tag_id).delete()
        db.delete(tag)
        db.commit()
        return True


tag_service = TagService()

