"""
Pydantic schemas for Person entity.
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class PersonBase(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=255, description="Full name of person")
    relationship: Optional[str] = Field(None, max_length=100, description="Relationship, e.g. Mother, Grandfather")
    biography: Optional[str] = Field(None, description="Brief biographical background")


class PersonCreate(PersonBase):
    pass


class PersonRead(PersonBase):
    id: str
    created_at: datetime
    memories_count: Optional[int] = 0

    model_config = ConfigDict(from_attributes=True)


class PersonSimple(BaseModel):
    id: str
    full_name: str
    relationship: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

