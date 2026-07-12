from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.meeting_intelligence import (
    AnalyzeMeetingRequest,
    MeetingAnalysisResponse,
)
from app.services.meeting_intelligence import analyze_meeting

router = APIRouter(prefix="/meetings", tags=["meetings"])


@router.post("/analyze", response_model=MeetingAnalysisResponse)
def analyze_meeting_endpoint(
    req: AnalyzeMeetingRequest,
    db: Session = Depends(get_db),
) -> MeetingAnalysisResponse:
    if req.meeting_id is None and not req.notes:
        raise HTTPException(
            status_code=422,
            detail="Provide either meeting_id or notes.",
        )
    try:
        return analyze_meeting(
            db,
            meeting_id=req.meeting_id,
            notes=req.notes,
            project_id=req.project_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:  # last-resort catch so the response is JSON, not HTML
        raise HTTPException(status_code=500, detail=f"Workflow error: {exc}")