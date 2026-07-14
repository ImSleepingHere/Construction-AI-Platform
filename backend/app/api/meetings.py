"""Read-only access to meetings and their decisions.

Note: this is unrelated to the meeting_intelligence agent (POST
/agents/meeting_intelligence) -- that analyzes notes with an LLM. This is
just a plain browse-the-dataset view over the meetings/project_decisions
tables.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.construction import Meeting, ProjectDecision
from app.schemas.construction import DecisionRead, MeetingRead, MeetingWithDecisionsRead

router = APIRouter(prefix="/meetings", tags=["meetings"])


@router.get("", response_model=list[MeetingRead])
def list_meetings(
    project_id: Optional[int] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
) -> list[Meeting]:
    q = db.query(Meeting)
    if project_id is not None:
        q = q.filter(Meeting.project_id == project_id)
    return q.order_by(Meeting.meeting_date.desc()).offset(offset).limit(limit).all()


@router.get("/{meeting_id}", response_model=MeetingWithDecisionsRead)
def get_meeting(meeting_id: int, db: Session = Depends(get_db)) -> MeetingWithDecisionsRead:
    meeting = db.get(Meeting, meeting_id)
    if meeting is None:
        raise HTTPException(status_code=404, detail="Meeting not found")

    decisions = (
        db.query(ProjectDecision)
        .filter(ProjectDecision.meeting_id == meeting_id)
        .order_by(ProjectDecision.decision_date.desc())
        .all()
    )
    return MeetingWithDecisionsRead(
        id=meeting.id,
        project_id=meeting.project_id,
        meeting_date=meeting.meeting_date,
        title=meeting.title,
        meeting_type=meeting.meeting_type,
        decisions=[DecisionRead.model_validate(d) for d in decisions],
    )
