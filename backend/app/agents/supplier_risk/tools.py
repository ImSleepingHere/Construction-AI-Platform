"""Domain tools for the supplier_risk agent.

All tools query the dataset's own tables (never modify them) and return
JSON-serializable dicts/lists. Floats are rounded to keep tool output compact
for the LLM's context.
"""

from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.agents.tools import tool
from app.models.construction import NCR, Project, PurchaseOrder, Supplier


@tool(
    name="get_supplier_delivery_stats",
    description=(
        "Return delivery performance stats for a supplier, derived from its "
        "purchase order history: on-time rate, average delay, and common "
        "delay root causes. Use this to ground any claim about lateness."
    ),
)
def get_supplier_delivery_stats(db: Session, supplier_id: int) -> dict:
    pos = (
        db.query(PurchaseOrder)
        .filter(PurchaseOrder.supplier_id == supplier_id)
        .all()
    )
    po_count = len(pos)
    if po_count == 0:
        return {
            "supplier_id": supplier_id,
            "po_count": 0,
            "late_count": 0,
            "on_time_rate": None,
            "avg_delay_days": None,
            "total_delay_days": 0,
            "most_recent_po_date": None,
            "distinct_root_causes": [],
        }

    late = [p for p in pos if p.is_late]
    late_count = len(late)
    total_delay_days = sum(p.delay_days for p in pos)
    avg_delay_days = round(total_delay_days / late_count, 2) if late_count else 0.0
    root_causes = sorted({p.delay_root_cause for p in late if p.delay_root_cause})

    return {
        "supplier_id": supplier_id,
        "po_count": po_count,
        "late_count": late_count,
        "on_time_rate": round((po_count - late_count) / po_count, 3),
        "avg_delay_days": avg_delay_days,
        "total_delay_days": total_delay_days,
        "most_recent_po_date": max(p.issue_date for p in pos),
        "distinct_root_causes": root_causes,
    }


@tool(
    name="get_supplier_quality_stats",
    description=(
        "Return quality issue stats for a supplier, derived from non-conformance "
        "reports (NCRs): count by status and sample root causes. Use this to "
        "ground any claim about quality problems."
    ),
)
def get_supplier_quality_stats(db: Session, supplier_id: int) -> dict:
    ncrs = db.query(NCR).filter(NCR.supplier_id == supplier_id).all()
    ncr_count = len(ncrs)
    if ncr_count == 0:
        return {
            "supplier_id": supplier_id,
            "ncr_count": 0,
            "by_status": {},
            "sample_root_causes": [],
            "most_recent_ncr_date": None,
        }

    by_status: dict[str, int] = {}
    for n in ncrs:
        by_status[n.status] = by_status.get(n.status, 0) + 1
    sample_root_causes = sorted({n.root_cause for n in ncrs if n.root_cause})[:5]

    return {
        "supplier_id": supplier_id,
        "ncr_count": ncr_count,
        "by_status": by_status,
        "sample_root_causes": sample_root_causes,
        "most_recent_ncr_date": max(n.issue_date for n in ncrs),
    }


@tool(
    name="get_supplier_projects",
    description=(
        "Return the distinct projects a supplier has delivered purchase orders "
        "for, with a per-project PO count. Use this to understand how "
        "concentrated or spread out a supplier's work is."
    ),
)
def get_supplier_projects(db: Session, supplier_id: int) -> list[dict]:
    rows = (
        db.query(Project, func.count(PurchaseOrder.id).label("po_count"))
        .join(PurchaseOrder, PurchaseOrder.project_id == Project.id)
        .filter(PurchaseOrder.supplier_id == supplier_id)
        .group_by(Project.id)
        .order_by(func.count(PurchaseOrder.id).desc())
        .all()
    )
    return [
        {
            "project_id": p.id,
            "name": p.project_name,
            "city": p.city,
            "status": p.status,
            "po_count_from_this_supplier": po_count,
        }
        for p, po_count in rows
    ]


@tool(
    name="get_supplier_profile",
    description="Return a supplier's basic profile: name, category, city, status.",
)
def get_supplier_profile(db: Session, supplier_id: int) -> dict:
    s = db.get(Supplier, supplier_id)
    if s is None:
        return {"error": "not found"}
    return {
        "supplier_id": s.id,
        "supplier_name": s.supplier_name,
        "category": s.category,
        "city": s.city,
        "status": s.status,
    }


@tool(
    name="list_suppliers_by_category",
    description=(
        "List suppliers filtered by category and optionally city. Use this to "
        "find alternative/backup suppliers in the same category."
    ),
)
def list_suppliers_by_category(
    db: Session, category: str, city: str = "", limit: int = 10
) -> list[dict]:
    q = db.query(Supplier).filter(Supplier.category.ilike(f"%{category}%"))
    if city:
        q = q.filter(Supplier.city.ilike(f"%{city}%"))
    limit = max(1, min(int(limit), 50))
    rows = q.order_by(Supplier.id).limit(limit).all()
    return [
        {
            "id": s.id,
            "supplier_name": s.supplier_name,
            "category": s.category,
            "city": s.city,
            "status": s.status,
        }
        for s in rows
    ]
