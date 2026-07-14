"""Domain tools for the executive_report agent.

"Recent" windows are anchored to each table's own most recent row, not
wall-clock today. The dataset's tables were generated with different max
dates (NCRs top out around 2025-01, safety_events around 2026-05, purchase
order promised_delivery extends into 2026-07+) -- none of which reliably
track the real present. Anchoring to wall-clock "today" would make a 7-day
window return zero NCRs and zero safety events on every single run, which
defeats the point of a weekly report. Anchoring to "N days before this
table's latest row" always yields a meaningful window.

Dates in the dataset are ISO text columns; comparisons use date.fromisoformat.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.agents.tools import tool
from app.models.construction import NCR, Project, PurchaseOrder, SafetyEvent

# Fixed lookback for "recent NCR" in get_projects_at_risk, which has no days
# parameter of its own (unlike the other recency-windowed tools). Note: ncrs
# has no severity column in this dataset (only safety_events does), so this
# flags on recent NCR volume, not severity.
AT_RISK_NCR_WINDOW_DAYS = 30


def _parse_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _latest_date(db: Session, date_column) -> date:
    """Most recent date in a table's date column, falling back to today if empty."""
    max_value = db.query(func.max(date_column)).scalar()
    return _parse_date(max_value) or date.today()


@tool(
    name="list_active_projects",
    description="List projects that are not Completed or Cancelled. Use this for a portfolio overview.",
)
def list_active_projects(db: Session, limit: int = 20) -> list[dict]:
    limit = max(1, min(int(limit), 100))
    rows = (
        db.query(Project)
        .filter(Project.status.notin_(["Completed", "Cancelled"]))
        .order_by(Project.id)
        .limit(limit)
        .all()
    )
    return [
        {
            "project_id": p.id,
            "project_name": p.project_name,
            "project_type": p.project_type,
            "city": p.city,
            "status": p.status,
            "planned_finish": p.planned_finish,
        }
        for p in rows
    ]


@tool(
    name="get_overdue_purchase_orders",
    description=(
        "Return purchase orders that are late and whose promised delivery fell "
        "within the last N days. Use this to spot fresh delivery risk."
    ),
)
def get_overdue_purchase_orders(db: Session, days: int = 7, limit: int = 20) -> list[dict]:
    limit = max(1, min(int(limit), 100))
    cutoff = _latest_date(db, PurchaseOrder.promised_delivery) - timedelta(days=days)

    rows = (
        db.query(PurchaseOrder)
        .filter(PurchaseOrder.is_late == 1)
        .order_by(PurchaseOrder.promised_delivery.desc())
        .all()
    )
    filtered = [p for p in rows if (_parse_date(p.promised_delivery) or date.min) >= cutoff]

    return [
        {
            "po_id": p.id,
            "po_number": p.po_number,
            "project_id": p.project_id,
            "supplier_id": p.supplier_id,
            "promised_delivery": p.promised_delivery,
            "delay_days": p.delay_days,
            "delay_root_cause": p.delay_root_cause,
        }
        for p in filtered[:limit]
    ]


@tool(
    name="get_recent_ncrs",
    description="Return non-conformance reports (NCRs) raised in the last N days.",
)
def get_recent_ncrs(db: Session, days: int = 7, limit: int = 20) -> list[dict]:
    limit = max(1, min(int(limit), 100))
    cutoff = _latest_date(db, NCR.issue_date) - timedelta(days=days)

    rows = db.query(NCR).order_by(NCR.issue_date.desc()).all()
    filtered = [n for n in rows if (_parse_date(n.issue_date) or date.min) >= cutoff]

    return [
        {
            "ncr_id": n.id,
            "project_id": n.project_id,
            "supplier_id": n.supplier_id,
            "ncr_type": n.ncr_type,
            "description": n.description,
            "issue_date": n.issue_date,
            "status": n.status,
        }
        for n in filtered[:limit]
    ]


@tool(
    name="get_recent_safety_events",
    description=(
        "Return safety events from the last N days, prioritizing high severity "
        "first. Use this to surface safety concerns for the weekly report."
    ),
)
def get_recent_safety_events(db: Session, days: int = 7, limit: int = 10) -> list[dict]:
    limit = max(1, min(int(limit), 100))
    cutoff = _latest_date(db, SafetyEvent.event_date) - timedelta(days=days)

    rows = db.query(SafetyEvent).all()
    filtered = [e for e in rows if (_parse_date(e.event_date) or date.min) >= cutoff]

    severity_rank = {"High": 0, "Medium": 1, "Low": 2}
    filtered.sort(
        key=lambda e: (severity_rank.get(e.severity, 3), e.event_date), reverse=False
    )

    return [
        {
            "event_id": e.id,
            "project_id": e.project_id,
            "event_date": e.event_date,
            "severity": e.severity,
            "description": e.description,
            "corrective_action": e.corrective_action,
        }
        for e in filtered[:limit]
    ]


@tool(
    name="get_projects_at_risk",
    description=(
        "Return projects that are either Delayed or have recent NCRs (non-"
        "conformance reports; this dataset's NCRs have no severity field, so "
        "this flags on recent NCR volume), each with a risk_reason explaining "
        "why it was flagged."
    ),
)
def get_projects_at_risk(db: Session, limit: int = 10) -> list[dict]:
    limit = max(1, min(int(limit), 50))
    cutoff = _latest_date(db, NCR.issue_date) - timedelta(days=AT_RISK_NCR_WINDOW_DAYS)

    delayed = {p.id: p for p in db.query(Project).filter(Project.status == "Delayed").all()}

    recent_ncrs = [
        n
        for n in db.query(NCR).all()
        if (_parse_date(n.issue_date) or date.min) >= cutoff
    ]
    ncr_project_ids = {n.project_id for n in recent_ncrs}
    ncr_projects = (
        db.query(Project).filter(Project.id.in_(ncr_project_ids)).all()
        if ncr_project_ids
        else []
    )

    at_risk: dict[int, dict] = {}
    for p in delayed.values():
        at_risk[p.id] = {
            "project_id": p.id,
            "project_name": p.project_name,
            "status": p.status,
            "risk_reason": "Project status is Delayed.",
        }

    ncr_counts: dict[int, int] = {}
    for n in recent_ncrs:
        ncr_counts[n.project_id] = ncr_counts.get(n.project_id, 0) + 1

    for p in ncr_projects:
        reason = (
            f"{ncr_counts.get(p.id, 0)} NCR(s) raised in the last "
            f"{AT_RISK_NCR_WINDOW_DAYS} days."
        )
        if p.id in at_risk:
            at_risk[p.id]["risk_reason"] += f" Also: {reason}"
        else:
            at_risk[p.id] = {
                "project_id": p.id,
                "project_name": p.project_name,
                "status": p.status,
                "risk_reason": reason,
            }

    return list(at_risk.values())[:limit]
