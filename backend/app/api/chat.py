"""POST /chat -- routes a free-text message to the right domain agent.

Users don't need to know meeting_intelligence/supplier_risk/executive_report
exist; they just describe what they want. An intent classifier picks the
agent (or answers directly for anything none of the three are built for).
"""

from __future__ import annotations

import time
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session

from app.agents.registry import get_agent
from app.core.database import get_db
from app.models.ai_layer import AIAuditLog
from app.services.intent_router import DOMAIN_AGENTS, classify_intent
from app.services.llm_client import get_llm_client

router = APIRouter(tags=["chat"])


class ChatRequest(BaseModel):
    message: str
    project_id: Optional[int] = None
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    agent_used: Optional[str]
    response: Any
    audit_log_id: int
    latency_ms: int


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    llm = get_llm_client()
    start = time.perf_counter()

    agent_descriptions = {name: get_agent(name).skill.description for name in DOMAIN_AGENTS}

    try:
        classification, classify_result = classify_intent(
            llm, req.message, agent_descriptions
        )
    except (ValidationError, ValueError) as exc:
        raise HTTPException(
            status_code=502, detail=f"Intent classification failed: {exc}"
        )

    if classification.agent == "none":
        latency_ms = int((time.perf_counter() - start) * 1000)
        audit = AIAuditLog(
            workflow="chat",
            project_id=req.project_id,
            model=classify_result.model,
            prompt=req.message,
            system_instruction="intent_router",
            output=classify_result.text,
            output_valid=True,
            prompt_tokens=classify_result.prompt_tokens,
            completion_tokens=classify_result.completion_tokens,
            latency_ms=latency_ms,
            metadata_json={"agent_used": None},
        )
        db.add(audit)
        db.commit()
        return ChatResponse(
            agent_used=None,
            response=classification.plain_response,
            audit_log_id=audit.id,
            latency_ms=latency_ms,
        )

    agent_input: dict[str, Any]
    if classification.agent == "meeting_intelligence":
        agent_input = {"notes": classification.meeting_notes or req.message}
        if req.project_id is not None:
            agent_input["project_id"] = req.project_id
    elif classification.agent == "supplier_risk":
        agent_input = {"supplier_id": classification.supplier_id}
    else:  # executive_report
        agent_input = {}

    agent = get_agent(classification.agent)
    result = agent.run(db, agent_input)
    latency_ms = int((time.perf_counter() - start) * 1000)

    return ChatResponse(
        agent_used=classification.agent,
        response=result.output.model_dump() if result.output else {"error": result.error},
        audit_log_id=result.audit_log_id,
        latency_ms=latency_ms,
    )
