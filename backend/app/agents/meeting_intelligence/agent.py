from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.agents.base import AgentContext, BaseAgent
from app.agents.meeting_intelligence.schemas import MeetingAnalysis
from app.models.construction import Meeting, ProjectDecision


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


class MeetingIntelligenceAgent(BaseAgent):
    skill_path = __file__
    output_model = MeetingAnalysis

    def prepare_input(self, ctx: AgentContext) -> str:
        meeting_id = ctx.input.get("meeting_id")
        notes = ctx.input.get("notes")
        project_id = ctx.input.get("project_id")

        if meeting_id is not None:
            notes_text, meta, meeting_project_id = self._load_meeting_notes(ctx.db, meeting_id)
            ctx.project_id = project_id or meeting_project_id
            ctx.retrieved_source_ids = [{"type": "meeting", "id": meeting_id}]
        elif notes:
            notes_text = notes
            meta = None
            ctx.project_id = project_id
        else:
            raise ValueError("Either meeting_id or notes must be provided")

        return _build_prompt(notes_text, meta)

    def on_success(self, ctx: AgentContext, output: MeetingAnalysis) -> None:
        for decision in output.decisions:
            content = decision.description
            if decision.rationale:
                content += f" — rationale: {decision.rationale}"
            ctx.store_memory(
                category="decision", content=content, confidence=output.confidence
            )

        for risk in output.risks:
            ctx.store_memory(
                category="risk",
                content=f"[{risk.severity}] {risk.description}",
                confidence=output.confidence,
            )

        for item in output.action_items:
            due_part = f" (due {item.due_date})" if item.due_date else ""
            ctx.store_memory(
                category="action_item",
                content=f"[{item.priority}] {item.description} — owner: {item.owner}{due_part}",
                confidence=output.confidence,
            )

    def _load_meeting_notes(
        self, db: Session, meeting_id: int
    ) -> tuple[str, dict, Optional[int]]:
        """Reconstruct meeting notes from the dataset.

        Our dataset's `meetings` table stores metadata only (date, title,
        type). The actual content is inferred from linked `project_decisions`.
        We synthesize a plausible 'notes' text from those records so the
        workflow has something to work on.
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
