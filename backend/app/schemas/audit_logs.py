"""Pydantic response schemas for the audit log."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


class AIAuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workflow: str
    project_id: Optional[int] = None
    model: str
    prompt: str
    system_instruction: Optional[str] = None
    output: Optional[str] = None
    output_valid: bool
    error: Optional[str] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    latency_ms: Optional[int] = None
    retrieved_source_ids: Optional[list[Any]] = None
    metadata_json: Optional[dict[str, Any]] = None
    created_at: datetime


class AIAuditLogPage(BaseModel):
    items: list[AIAuditLogRead]
    total: int
    limit: int
    offset: int
