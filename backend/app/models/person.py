"""
Person model representing ancestors, relatives, or individuals connected to memories.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.orm import relationship as sa_relationship

from backend.app.database.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Person(Base):
    __tablename__ = "people"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    full_name = Column(String(255), nullable=False, index=True)
    relationship = Column("relationship", String(100), nullable=True)  # e.g., Grandmother, Father, Self
    biography = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    # Relationships
    memory_associations = sa_relationship(
        "MemoryPerson",
        back_populates="person",
        cascade="all, delete-orphan"
    )
    memories = sa_relationship(
        "Memory",
        secondary="memory_people",
        viewonly=True
    )
