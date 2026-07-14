"""Access to the human-in-the-loop approval queue.

Any workflow that needs review before acting writes an ApprovalRequest row
(see app.models.ai_layer.ApprovalRequest) instead of executing directly.
Nothing currently writes to this queue -- it's plumbed and ready for a
future workflow to use, but no agent routes through it yet. approve/reject
are the one write surface here: they only transition a pending row to
approved/rejected, nothing else.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.ai_layer import ApprovalRequest
from app.schemas.approvals import ApprovalRequestPage, ApprovalRequestRead, ReviewRequest

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


def _review(
    approval_id: int, body: ReviewRequest, new_status: str, db: Session
) -> ApprovalRequest:
    row = db.get(ApprovalRequest, approval_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Approval request not found")
    if row.status != "pending":
        raise HTTPException(
            status_code=409, detail=f"Approval request is already {row.status}"
        )

    row.status = new_status
    row.reviewer = body.reviewer
    row.reviewed_at = datetime.now(timezone.utc)
    row.review_notes = body.notes
    db.commit()
    db.refresh(row)
    return row


@router.post("/{approval_id}/approve", response_model=ApprovalRequestRead)
def approve_request(
    approval_id: int, body: ReviewRequest, db: Session = Depends(get_db)
) -> ApprovalRequest:
    return _review(approval_id, body, "approved", db)


@router.post("/{approval_id}/reject", response_model=ApprovalRequestRead)
def reject_request(
    approval_id: int, body: ReviewRequest, db: Session = Depends(get_db)
) -> ApprovalRequest:
    return _review(approval_id, body, "rejected", db)
