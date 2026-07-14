"""Pydantic response schemas for ai_memories."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


class AIMemoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: Optional[int] = None
    category: str
    content: str
    source_reference: dict[str, Any]
    confidence: float
    extracted_by: str
    created_at: datetime


class AIMemoryPage(BaseModel):
    items: list[AIMemoryRead]
    total: int
    limit: int
    offset: int
