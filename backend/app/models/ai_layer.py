"""SQLAlchemy models for the AI layer.

These four tables underpin every AI workflow:
- ai_memories:      structured facts the system has extracted, with source citations
- ai_audit_logs:    full trace of every LLM call (prompt, model, cost, latency)
- approval_requests: human-in-the-loop queue for actions needing review
- document_chunks:  text chunks + vector embeddings for RAG
"""

from datetime import datetime
from typing import Any, Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


# The embedding model (Gemini text-embedding-004) produces 768-dim vectors.
# If you swap to a different embedding model later, this must match.
EMBEDDING_DIM = 768


class AIMemory(Base):
    """A structured fact extracted by an AI workflow.

    Categories: decision, risk, action_item, lesson_learned, blocker, insight.
    Every memory MUST cite its source (a document chunk, a meeting, a raw text
    payload the workflow received). Empty source_reference is disallowed at the
    application layer.
    """

    __tablename__ = "ai_memories"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, index=True
    )
    category: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source_reference: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    confidence: Mapped[float] = mapped_column(nullable=False, default=0.0)
    extracted_by: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )


class AIAuditLog(Base):
    """Full trace of a single LLM call.

    Every workflow call MUST write one row here BEFORE returning to the user.
    This is what makes AI responses reproducible and auditable — the core
    difference between a demo and a system that could be piloted.
    """

    __tablename__ = "ai_audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    workflow: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    project_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, index=True
    )
    model: Mapped[str] = mapped_column(String(64), nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    system_instruction: Mapped[Optional[str]] = mapped_column(Text)
    output: Mapped[Optional[str]] = mapped_column(Text)
    output_valid: Mapped[bool] = mapped_column(nullable=False, default=True)
    error: Mapped[Optional[str]] = mapped_column(Text)
    prompt_tokens: Mapped[Optional[int]] = mapped_column(Integer)
    completion_tokens: Mapped[Optional[int]] = mapped_column(Integer)
    latency_ms: Mapped[Optional[int]] = mapped_column(Integer)
    retrieved_source_ids: Mapped[Optional[list[Any]]] = mapped_column(JSONB)
    metadata_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )


class ApprovalRequest(Base):
    """A pending action awaiting human review.

    Any workflow that would send external communication, update contractual
    data, or make a consequential change routes through this queue instead of
    executing directly.
    """

    __tablename__ = "approval_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    workflow: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    project_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, index=True
    )
    action_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)
    source_ids: Mapped[list[Any]] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="pending", index=True
    )
    reviewer: Mapped[Optional[str]] = mapped_column(String(128))
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    review_notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )


class DocumentChunk(Base):
    """A chunk of a document with its embedding, for RAG retrieval.

    Documents in the source dataset (emails, meeting notes, etc.) get chunked
    into ~500-token segments, embedded via Gemini, and stored here. The
    workflow's memory-search step queries this table by vector similarity.
    """

    __tablename__ = "document_chunks"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    source_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    project_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, index=True
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIM), nullable=False)
    token_count: Mapped[Optional[int]] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )