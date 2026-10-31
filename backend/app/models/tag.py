"""
MemoryTag model for categorization.
Phase 2: Full user-editable tags with default heritage taxonomy.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime
from sqlalchemy.orm import relationship

from backend.app.database.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class MemoryTag(Base):
    __tablename__ = "memory_tags"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    # Relationships
    memories = relationship(
        "Memory",
        secondary="memory_tag_associations",
        back_populates="tags"
    )
