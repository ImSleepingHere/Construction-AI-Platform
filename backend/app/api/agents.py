"""Auto-generated endpoints over the agent registry.

GET  /agents            -> list registered agents (name, description, version)
POST /agents/{skill}     -> run an agent; body is {"input": {...arbitrary...}}
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.agents.registry import get_agent, list_agents
from app.core.database import get_db

router = APIRouter(prefix="/agents", tags=["agents"])


class AgentRunRequest(BaseModel):
    input: dict[str, Any]


@router.get("")
def list_agents_endpoint() -> list[dict[str, str]]:
    return list_agents()


@router.post("/{skill_name}")
def run_agent_endpoint(
    skill_name: str,
    req: AgentRunRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    try:
        agent = get_agent(skill_name)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    result = agent.run(db, req.input)

    response: dict[str, Any] = dict(result.output.model_dump()) if result.output else {}
    response.update(
        {
            "audit_log_id": result.audit_log_id,
            "model": result.model,
            "latency_ms": result.latency_ms,
            "turns_used": result.turns_used,
            "tool_call_trace": result.tool_call_trace,
            "memory_ids": result.memory_ids,
            "output_valid": result.output_valid,
            "error": result.error,
        }
    )
    return response
