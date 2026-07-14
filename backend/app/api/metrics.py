"""Observability endpoints: aggregate stats over ai_audit_logs/ai_memories.

Everything here is a SQL aggregate (GROUP BY / jsonb_array_elements), not a
Python loop over rows -- these tables can grow large and this is meant to
stay cheap regardless of row count.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db

router = APIRouter(prefix="/metrics", tags=["metrics"])

# Rough, illustrative estimate only -- not tied to any specific Gemini price
# tier. Good enough to show relative cost trends across agents/runs.
COST_PER_1K_TOKENS_USD = 0.00015


@router.get("/agents")
def agent_metrics(db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    rows = db.execute(
        text(
            """
            SELECT
                workflow,
                COUNT(*) AS total_runs,
                ROUND(AVG(CASE WHEN output_valid THEN 1.0 ELSE 0.0 END)::numeric, 3) AS success_rate,
                ROUND(AVG(latency_ms)::numeric, 1) AS avg_latency_ms,
                ROUND(AVG(COALESCE(prompt_tokens, 0) + COALESCE(completion_tokens, 0))::numeric, 1) AS avg_tokens,
                MAX(created_at) AS last_run_at
            FROM ai_audit_logs
            GROUP BY workflow
            ORDER BY total_runs DESC
            """
        )
    ).mappings().all()
    return [dict(r) for r in rows]


@router.get("/tools")
def tool_metrics(db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    rows = db.execute(
        text(
            """
            SELECT
                trace ->> 'tool' AS tool,
                COUNT(*) AS total_invocations,
                ROUND(AVG(LENGTH((trace -> 'output')::text))::numeric, 1) AS avg_output_size_chars,
                ROUND(AVG(CASE WHEN trace ->> 'error' IS NOT NULL THEN 1.0 ELSE 0.0 END)::numeric, 3) AS error_rate
            FROM ai_audit_logs,
                 jsonb_array_elements(COALESCE(metadata_json -> 'tool_call_trace', '[]'::jsonb)) AS trace
            GROUP BY trace ->> 'tool'
            ORDER BY total_invocations DESC
            """
        )
    ).mappings().all()
    return [dict(r) for r in rows]


@router.get("/overview")
def overview_metrics(db: Session = Depends(get_db)) -> dict[str, Any]:
    llm = db.execute(
        text(
            """
            SELECT
                COUNT(*) AS total_llm_calls,
                COALESCE(SUM(COALESCE(prompt_tokens, 0) + COALESCE(completion_tokens, 0)), 0) AS total_tokens
            FROM ai_audit_logs
            """
        )
    ).mappings().one()

    memory_count = db.execute(text("SELECT COUNT(*) FROM ai_memories")).scalar_one()
    chunk_count = db.execute(text("SELECT COUNT(*) FROM document_chunks")).scalar_one()
    audit_log_count = db.execute(text("SELECT COUNT(*) FROM ai_audit_logs")).scalar_one()

    total_tokens = int(llm["total_tokens"])
    return {
        "total_llm_calls": llm["total_llm_calls"],
        "total_tokens": total_tokens,
        "estimated_cost_usd": round(total_tokens / 1000 * COST_PER_1K_TOKENS_USD, 4),
        "cost_estimate_note": f"Rough estimate at ${COST_PER_1K_TOKENS_USD}/1K tokens -- not tied to actual billing.",
        "audit_log_count": audit_log_count,
        "memory_count": memory_count,
        "document_chunk_count": chunk_count,
    }
