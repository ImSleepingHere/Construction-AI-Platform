"""Read-only access to the human-in-the-loop approval queue.

Any workflow that needs review before acting writes an ApprovalRequest row
(see app.models.ai_layer.ApprovalRequest) instead of executing directly.
Nothing currently writes to this queue -- it's plumbed and ready for a
future workflow to use, but no agent routes through it yet.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.ai_layer import ApprovalRequest
from app.schemas.approvals import ApprovalRequestPage, ApprovalRequestRead

router = APIRouter(prefix="/approvals", tags=["approvals"])


@router.get("", response_model=ApprovalRequestPage)
def list_approvals(
    status: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db),
) -> ApprovalRequestPage:
    limit = max(1, min(limit, 100))
    offset = max(0, offset)

    q = db.query(ApprovalRequest)
    if status:
        q = q.filter(ApprovalRequest.status == status)

    total = q.count()
    rows = q.order_by(ApprovalRequest.created_at.desc()).offset(offset).limit(limit).all()

    return ApprovalRequestPage(
        items=[ApprovalRequestRead.model_validate(r) for r in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{approval_id}", response_model=ApprovalRequestRead)
def get_approval(approval_id: int, db: Session = Depends(get_db)) -> ApprovalRequest:
    row = db.get(ApprovalRequest, approval_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Approval request not found")
    return row
