"""Meeting Intelligence workflow.

Turns raw meeting notes into structured analysis: summary, action items,
decisions, risks. Persists results as memories and logs the full LLM call.
"""

from __future__ import annotations

import json
import time
from typing import Optional

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.models.ai_layer import AIAuditLog, AIMemory
from app.models.construction import Meeting, ProjectDecision
from app.schemas.meeting_intelligence import (
    MeetingAnalysis,
    MeetingAnalysisResponse,
)
from app.services.llm_client import LLMClient, get_llm_client


WORKFLOW_NAME = "meeting_intelligence"

SYSTEM_INSTRUCTION = """You are a senior construction project manager assistant. \
You analyze meeting notes and extract structured, grounded information.

RULES YOU MUST FOLLOW:
1. Only report items that are actually in the notes. Do not invent action items, \
decisions, or risks that were not discussed.
2. Every action item must have an owner. If the notes don't name one, use "Unassigned".
3. Dates must be in ISO format (YYYY-MM-DD) or null. Do not guess dates.
4. If a section has nothing to report (e.g., no risks discussed), return an empty list.
5. `confidence` should reflect how clear the notes were. Vague notes = low confidence.
6. Reply with a single JSON object matching the required schema. No prose before \
or after the JSON.
"""


def _build_prompt(notes: str, meeting_metadata: Optional[dict] = None) -> str:
    """Assemble the user prompt with meeting notes and any metadata."""
    parts = []
    if meeting_metadata:
        parts.append("MEETING METADATA:")
        for key, value in meeting_metadata.items():
            if value is not None:
                parts.append(f"- {key}: {value}")
        parts.append("")
    parts.append("MEETING NOTES:")
    parts.append(notes.strip())
    parts.append("")
    parts.append(
        "Extract the structured analysis as JSON. Follow the schema strictly."
    )
    return "\n".join(parts)


def _load_meeting_notes(
    db: Session, meeting_id: int
) -> tuple[str, dict, Optional[int]]:
    """Reconstruct meeting notes from the dataset.

    Our dataset's `meetings` table stores metadata only (date, title, type). The
    actual content is inferred from linked `project_decisions`. We synthesize a
    plausible 'notes' text from those records so the workflow has something to
    work on.
    """
    meeting = db.get(Meeting, meeting_id)
    if meeting is None:
        raise ValueError(f"Meeting {meeting_id} not found")

    decisions = (
        db.query(ProjectDecision)
        .filter(ProjectDecision.meeting_id == meeting_id)
        .order_by(ProjectDecision.id)
        .all()
    )

    lines = [
        f"Meeting: {meeting.title}",
        f"Date: {meeting.meeting_date}",
        f"Type: {meeting.meeting_type}",
        "",
    ]
    if decisions:
        lines.append("Discussion points recorded:")
        for d in decisions:
            owner_part = f" (owner: {d.owner})" if d.owner else ""
            lines.append(f"- {d.decision_text}{owner_part}")
    else:
        lines.append("(No detailed discussion points recorded for this meeting.)")

    notes = "\n".join(lines)
    metadata = {
        "title": meeting.title,
        "meeting_type": meeting.meeting_type,
        "date": meeting.meeting_date,
    }
    return notes, metadata, meeting.project_id


def analyze_meeting(
    db: Session,
    *,
    meeting_id: Optional[int] = None,
    notes: Optional[str] = None,
    project_id: Optional[int] = None,
    llm: Optional[LLMClient] = None,
) -> MeetingAnalysisResponse:
    """Run the Meeting Intelligence workflow end-to-end.

    Either `meeting_id` (to pull from the dataset) or `notes` (raw text) must
    be provided. Persists results as AI memories and always writes an audit log
    row before returning.
    """
    llm = llm or get_llm_client()

    # 1. Assemble input
    if meeting_id is not None:
        notes_text, meta, meeting_project_id = _load_meeting_notes(db, meeting_id)
        project_id = project_id or meeting_project_id
    elif notes:
        notes_text = notes
        meta = None
    else:
        raise ValueError("Either meeting_id or notes must be provided")

    prompt = _build_prompt(notes_text, meta)

    # 2. Call LLM with strict schema
    schema = MeetingAnalysis.model_json_schema()
    call_start = time.perf_counter()
    result = llm.generate(
        prompt=prompt,
        system_instruction=SYSTEM_INSTRUCTION,
        response_schema=schema,
        temperature=0.2,
    )
    total_latency_ms = int((time.perf_counter() - call_start) * 1000)

    # 3. Validate structured output
    analysis: Optional[MeetingAnalysis] = None
    validation_error: Optional[str] = None
    try:
        parsed = json.loads(result.text)
        analysis = MeetingAnalysis.model_validate(parsed)
    except (json.JSONDecodeError, ValidationError) as exc:
        validation_error = f"{type(exc).__name__}: {exc}"

    # 4. Write audit log FIRST — before persisting memories or returning.
    #    This guarantees every LLM call is traceable even if downstream fails.
    audit = AIAuditLog(
        workflow=WORKFLOW_NAME,
        project_id=project_id,
        model=result.model,
        prompt=prompt,
        system_instruction=SYSTEM_INSTRUCTION,
        output=result.text,
        output_valid=analysis is not None,
        error=validation_error,
        prompt_tokens=result.prompt_tokens,
        completion_tokens=result.completion_tokens,
        latency_ms=total_latency_ms,
        retrieved_source_ids=[{"type": "meeting", "id": meeting_id}] if meeting_id else [],
        metadata_json={"has_notes_metadata": meta is not None},
    )
    db.add(audit)
    db.flush()  # get audit.id without committing yet

    if analysis is None:
        db.commit()
        raise ValueError(
            f"LLM output failed validation: {validation_error}. "
            f"See audit log {audit.id} for the raw response."
        )

    # 5. Persist structured facts as memories
    memory_ids: list[int] = []
    source_ref = {
        "type": "meeting",
        "meeting_id": meeting_id,
        "audit_log_id": audit.id,
    }
    for decision in analysis.decisions:
        m = AIMemory(
            project_id=project_id,
            category="decision",
            content=decision.description
            + (f" — rationale: {decision.rationale}" if decision.rationale else ""),
            source_reference=source_ref,
            confidence=analysis.confidence,
            extracted_by=WORKFLOW_NAME,
        )
        db.add(m)
        db.flush()
        memory_ids.append(m.id)

    for risk in analysis.risks:
        m = AIMemory(
            project_id=project_id,
            category="risk",
            content=f"[{risk.severity}] {risk.description}",
            source_reference=source_ref,
            confidence=analysis.confidence,
            extracted_by=WORKFLOW_NAME,
        )
        db.add(m)
        db.flush()
        memory_ids.append(m.id)

    for item in analysis.action_items:
        due_part = f" (due {item.due_date})" if item.due_date else ""
        m = AIMemory(
            project_id=project_id,
            category="action_item",
            content=f"[{item.priority}] {item.description} — owner: {item.owner}{due_part}",
            source_reference=source_ref,
            confidence=analysis.confidence,
            extracted_by=WORKFLOW_NAME,
        )
        db.add(m)
        db.flush()
        memory_ids.append(m.id)

    db.commit()

    return MeetingAnalysisResponse(
        meeting_id=meeting_id,
        project_id=project_id,
        analysis=analysis,
        memory_ids=memory_ids,
        audit_log_id=audit.id,
        model=result.model,
        latency_ms=total_latency_ms,
    )