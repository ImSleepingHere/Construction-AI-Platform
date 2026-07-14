"""Read-only access to the LLM call audit trail.

Every agent/chat run writes exactly one ai_audit_logs row before returning
to the caller (see BaseAgent._write_audit_log and chat.py's 'none' branch).
This endpoint just surfaces that table -- nothing writes through it.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.ai_layer import AIAuditLog
from app.schemas.audit_logs import AIAuditLogPage, AIAuditLogRead

router = APIRouter(prefix="/audit-logs", tags=["audit-logs"])


@router.get("", response_model=AIAuditLogPage)
def list_audit_logs(
    workflow: Optional[str] = None,
    project_id: Optional[int] = None,
    output_valid: Optional[bool] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
) -> AIAuditLogPage:
    limit = max(1, min(limit, 200))
    offset = max(0, offset)

    q = db.query(AIAuditLog)
    if workflow:
        q = q.filter(AIAuditLog.workflow == workflow)
    if project_id is not None:
        q = q.filter(AIAuditLog.project_id == project_id)
    if output_valid is not None:
        q = q.filter(AIAuditLog.output_valid == output_valid)
    if date_from is not None:
        q = q.filter(AIAuditLog.created_at >= date_from)
    if date_to is not None:
        q = q.filter(AIAuditLog.created_at <= date_to)

    total = q.count()
    rows = q.order_by(AIAuditLog.created_at.desc()).offset(offset).limit(limit).all()

    return AIAuditLogPage(
        items=[AIAuditLogRead.model_validate(r) for r in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{audit_log_id}", response_model=AIAuditLogRead)
def get_audit_log(audit_log_id: int, db: Session = Depends(get_db)) -> AIAuditLog:
    row = db.get(AIAuditLog, audit_log_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Audit log not found")
    return row
