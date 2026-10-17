from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ComplaintStatus, ComplaintTargetType


class ComplaintCreate(BaseModel):
    target_type: ComplaintTargetType
    target_id: int
    reason: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)


class ComplaintUpdate(BaseModel):
    """Admin shikoyat holatini o'zgartiradi. RESOLVED/REJECTED bo'lsa
    resolved_by/resolved_at avtomatik to'ldiriladi."""

    status: ComplaintStatus


class ComplaintRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    reporter_id: int
    target_type: ComplaintTargetType
    target_id: int
    reason: str
    description: str | None
    status: ComplaintStatus
    resolved_by_id: int | None
    created_at: datetime
    resolved_at: datetime | None
