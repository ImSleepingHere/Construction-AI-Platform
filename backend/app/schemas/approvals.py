"""Pydantic response schemas for the approval queue."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


class ApprovalRequestRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workflow: str
    project_id: Optional[int] = None
    action_type: str
    payload: dict[str, Any]
    reasoning: str
    source_ids: list[Any]
    status: str
    reviewer: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    review_notes: Optional[str] = None
    created_at: datetime


class ApprovalRequestPage(BaseModel):
    items: list[ApprovalRequestRead]
    total: int
    limit: int
    offset: int


class ReviewRequest(BaseModel):
    reviewer: str
    notes: Optional[str] = None
