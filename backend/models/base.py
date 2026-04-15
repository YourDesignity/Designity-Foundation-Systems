"""Base model utilities shared across backend model domains."""

from datetime import date, datetime
from typing import Annotated, Any, Dict, Optional

from beanie import Document, Indexed
from pydantic import BaseModel, Field


def _coerce_date_to_datetime(v):
    """Convert datetime.date → datetime.datetime for BSON/MongoDB compatibility.

    pymongo's BSON codec does not natively support bare ``datetime.date``
    objects on all platforms (notably Windows). This helper is used as a
    ``mode='before'`` field validator in every Document that stores date
    fields so that values are always stored as ``datetime.datetime``.
    """
    if isinstance(v, date) and not isinstance(v, datetime):
        return datetime(v.year, v.month, v.day)
    return v


class Counter(Document):
    collection_name: Annotated[str, Indexed(unique=True)]
    current_uid: int = 0

    class Settings:
        name = "counters"


class MemoryNode(BaseModel):
    uid: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    is_active: bool = True
    specs: Dict[str, Any] = {}

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
