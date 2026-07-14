from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.construction import NCR, Meeting, Project, PurchaseOrder, SafetyEvent
from app.schemas.construction import (
    MeetingRead,
    NCRRead,
    ProjectRead,
    PurchaseOrderRead,
    SafetyEventRead,
)

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=list[ProjectRead])
def list_projects(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
) -> list[Project]:
    return db.query(Project).order_by(Project.id).offset(offset).limit(limit).all()


@router.get("/{project_id}", response_model=ProjectRead)
def get_project(project_id: int, db: Session = Depends(get_db)) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.get("/{project_id}/meetings", response_model=list[MeetingRead])
def list_project_meetings(
    project_id: int, limit: int = 100, offset: int = 0, db: Session = Depends(get_db)
) -> list[Meeting]:
    return (
        db.query(Meeting)
        .filter(Meeting.project_id == project_id)
        .order_by(Meeting.meeting_date.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


@router.get("/{project_id}/purchase-orders", response_model=list[PurchaseOrderRead])
def list_project_purchase_orders(
    project_id: int, limit: int = 100, offset: int = 0, db: Session = Depends(get_db)
) -> list[PurchaseOrder]:
    return (
        db.query(PurchaseOrder)
        .filter(PurchaseOrder.project_id == project_id)
        .order_by(PurchaseOrder.issue_date.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


@router.get("/{project_id}/ncrs", response_model=list[NCRRead])
def list_project_ncrs(
    project_id: int, limit: int = 100, offset: int = 0, db: Session = Depends(get_db)
) -> list[NCR]:
    return (
        db.query(NCR)
        .filter(NCR.project_id == project_id)
        .order_by(NCR.issue_date.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


@router.get("/{project_id}/safety-events", response_model=list[SafetyEventRead])
def list_project_safety_events(
    project_id: int, limit: int = 100, offset: int = 0, db: Session = Depends(get_db)
) -> list[SafetyEvent]:
    return (
        db.query(SafetyEvent)
        .filter(SafetyEvent.project_id == project_id)
        .order_by(SafetyEvent.event_date.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )