"""add AI layer tables

Revision ID: c47eeeb319b2
Revises: 
Create Date: 2026-07-12 05:52:34.164230

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision: str = 'c47eeeb319b2'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pgvector (idempotent — safe even if extension already exists)
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # AI memories — structured facts extracted by workflows
    op.create_table(
        "ai_memories",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=True),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("source_reference", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("extracted_by", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_memories_category", "ai_memories", ["category"])
    op.create_index("ix_ai_memories_created_at", "ai_memories", ["created_at"])
    op.create_index("ix_ai_memories_project_id", "ai_memories", ["project_id"])

    # AI audit logs — full trace of every LLM call
    op.create_table(
        "ai_audit_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("workflow", sa.String(length=64), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=True),
        sa.Column("model", sa.String(length=64), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("system_instruction", sa.Text(), nullable=True),
        sa.Column("output", sa.Text(), nullable=True),
        sa.Column("output_valid", sa.Boolean(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("retrieved_source_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_audit_logs_workflow", "ai_audit_logs", ["workflow"])
    op.create_index("ix_ai_audit_logs_project_id", "ai_audit_logs", ["project_id"])
    op.create_index("ix_ai_audit_logs_created_at", "ai_audit_logs", ["created_at"])

    # Approval requests — human-in-the-loop queue
    op.create_table(
        "approval_requests",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("workflow", sa.String(length=64), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=True),
        sa.Column("action_type", sa.String(length=64), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("reasoning", sa.Text(), nullable=False),
        sa.Column("source_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("reviewer", sa.String(length=128), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_approval_requests_workflow", "approval_requests", ["workflow"])
    op.create_index("ix_approval_requests_project_id", "approval_requests", ["project_id"])
    op.create_index("ix_approval_requests_status", "approval_requests", ["status"])
    op.create_index("ix_approval_requests_created_at", "approval_requests", ["created_at"])

    # Document chunks — text + embeddings for RAG
    op.create_table(
        "document_chunks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=True),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(768), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_document_chunks_source_type", "document_chunks", ["source_type"])
    op.create_index("ix_document_chunks_source_id", "document_chunks", ["source_id"])
    op.create_index("ix_document_chunks_project_id", "document_chunks", ["project_id"])
    # ### end Alembic commands ###


def downgrade() -> None:
    op.drop_index("ix_document_chunks_project_id", table_name="document_chunks")
    op.drop_index("ix_document_chunks_source_id", table_name="document_chunks")
    op.drop_index("ix_document_chunks_source_type", table_name="document_chunks")
    op.drop_table("document_chunks")

    op.drop_index("ix_approval_requests_created_at", table_name="approval_requests")
    op.drop_index("ix_approval_requests_status", table_name="approval_requests")
    op.drop_index("ix_approval_requests_project_id", table_name="approval_requests")
    op.drop_index("ix_approval_requests_workflow", table_name="approval_requests")
    op.drop_table("approval_requests")

    op.drop_index("ix_ai_audit_logs_created_at", table_name="ai_audit_logs")
    op.drop_index("ix_ai_audit_logs_project_id", table_name="ai_audit_logs")
    op.drop_index("ix_ai_audit_logs_workflow", table_name="ai_audit_logs")
    op.drop_table("ai_audit_logs")

    op.drop_index("ix_ai_memories_project_id", table_name="ai_memories")
    op.drop_index("ix_ai_memories_created_at", table_name="ai_memories")
    op.drop_index("ix_ai_memories_category", table_name="ai_memories")
    op.drop_table("ai_memories")
    # ### end Alembic commands ###
