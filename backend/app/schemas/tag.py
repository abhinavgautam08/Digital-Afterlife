"""
Pydantic schemas for MemoryTag entity.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class TagBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Tag name")


class TagCreate(TagBase):
    pass


class TagUpdate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)


class TagRead(TagBase):
    id: str
    created_at: Optional[datetime] = None
    memories_count: Optional[int] = 0

    model_config = ConfigDict(from_attributes=True)

