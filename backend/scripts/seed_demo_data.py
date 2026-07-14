"""Curate a coherent demo narrative from the (otherwise realistic-but-random)
dataset, and print DEMO_GUIDE.md at the repo root.

Picks 3 real projects that already tell a story (verified against the live
data, not invented) and adds a small amount of connective tissue -- one
meeting + decision, one fresh NCR -- so the three domain agents all surface
the same story when demoed back-to-back.

Idempotent: every row this script writes carries a "[DEMO]" marker; reruns
check for that marker before inserting.

Run inside the API container:
    python /app/scripts/seed_demo_data.py
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

from app.core.database import SessionLocal
from app.models.construction import Meeting, NCR, Project, ProjectDecision, Supplier

# Anchor projects, picked by querying the live data for the best fit in each
# role (see the session notes for the exact queries):
HEALTHY_PROJECT_ID = 28  # Tabuk Warehouse Project 28 -- Active, cleanest NCR/safety record
DELAYED_PROJECT_ID = 1  # Khobar School Project 1 -- Delayed, uses HIGH_RISK_SUPPLIER_ID
SAFETY_RISK_PROJECT_ID = 10  # Khobar Infrastructure Project 10 -- On Hold, 5 high-severity safety events

HIGH_RISK_SUPPLIER_ID = 1  # Risk Supplier 001 -- confirmed risk_score ~75 (high)
MEDIUM_RISK_SUPPLIER_ID = 54  # Supplier 054 -- confirmed risk_score ~60 (medium)
LOW_RISK_SUPPLIER_ID = 14  # Supplier 014 -- 27 POs/5 late, 1 NCR -- cleanest available

DEMO_MEETING_TITLE = "[DEMO] Weekly Coordination - Rebar Delay Review"
DEMO_NCR_MARKER = "[DEMO]"

DEMO_MEETING_NOTES = """\
Weekly coordination meeting, Khobar School Project 1.

Attendees: Site PM, Procurement Lead, QA/QC Manager.

Rebar delivery from Risk Supplier 001 is now 25 days behind the promised \
date, holding up the foundation pour on Block B. Procurement flagged this \
is the third late delivery from this supplier in the last two months.

Decision: switch the remaining rebar packages to a backup supplier in the \
Concrete category if Risk Supplier 001 cannot commit to a firm delivery \
date by end of week. Procurement Lead to own this and report back Friday.

Also raised: QA flagged a workmanship NCR on Risk Supplier 001's most \
recent delivery batch (surface finish out of tolerance). QA/QC Manager to \
track through to closure.

Risk: continued delay pushes the foundation pour past the concrete \
subcontractor's booked slot, which would cascade into a 2-week schedule \
slip for Block B.
"""


def _latest_ncr_date(db) -> date:
    from sqlalchemy import func

    max_date = db.query(func.max(NCR.issue_date)).scalar()
    try:
        return date.fromisoformat(max_date) if max_date else date.today()
    except ValueError:
        return date.today()


def seed(db) -> dict:
    summary: dict[str, object] = {"created": [], "already_present": []}

    # Sanity-check the anchor projects/suppliers actually exist -- fail loud
    # if the dataset ever changes under us rather than seeding garbage.
    for pid in (HEALTHY_PROJECT_ID, DELAYED_PROJECT_ID, SAFETY_RISK_PROJECT_ID):
        if db.get(Project, pid) is None:
            raise RuntimeError(f"Anchor project {pid} not found -- dataset changed?")
    for sid in (HIGH_RISK_SUPPLIER_ID, MEDIUM_RISK_SUPPLIER_ID, LOW_RISK_SUPPLIER_ID):
        if db.get(Supplier, sid) is None:
            raise RuntimeError(f"Anchor supplier {sid} not found -- dataset changed?")

    # 1. A meeting + decision on the delayed project, naming the high-risk
    #    supplier explicitly, for a good meeting_intelligence extraction.
    existing_meeting = (
        db.query(Meeting)
        .filter(Meeting.project_id == DELAYED_PROJECT_ID, Meeting.title == DEMO_MEETING_TITLE)
        .first()
    )
    if existing_meeting is None:
        meeting = Meeting(
            project_id=DELAYED_PROJECT_ID,
            meeting_date=date.today().isoformat(),
            title=DEMO_MEETING_TITLE,
            meeting_type="Coordination",
        )
        db.add(meeting)
        db.flush()

        decision = ProjectDecision(
            project_id=DELAYED_PROJECT_ID,
            meeting_id=meeting.id,
            decision_date=date.today().isoformat(),
            decision_text=(
                "Switch remaining rebar packages to a backup supplier if "
                "Risk Supplier 001 cannot commit to a firm delivery date by "
                "end of week."
            ),
            owner="Procurement Lead",
        )
        db.add(decision)
        db.flush()
        summary["created"].append(f"meeting {meeting.id} + decision {decision.id} on project {DELAYED_PROJECT_ID}")
        summary["meeting_id"] = meeting.id
    else:
        summary["already_present"].append(f"meeting on project {DELAYED_PROJECT_ID}")
        summary["meeting_id"] = existing_meeting.id

    # 2. A fresh NCR on the delayed project (existing NCRs there are 2+
    #    years stale relative to the dataset's own max date, so it wouldn't
    #    otherwise surface in executive_report's "recent" window).
    existing_ncr = (
        db.query(NCR)
        .filter(NCR.project_id == DELAYED_PROJECT_ID, NCR.description.like(f"{DEMO_NCR_MARKER}%"))
        .first()
    )
    if existing_ncr is None:
        recent_date = _latest_ncr_date(db) - timedelta(days=2)
        ncr = NCR(
            project_id=DELAYED_PROJECT_ID,
            supplier_id=HIGH_RISK_SUPPLIER_ID,
            ncr_type="Workmanship",
            description=f"{DEMO_NCR_MARKER} Surface finish on rebar delivery batch out of tolerance.",
            root_cause="Poor supplier QA process",
            issue_date=recent_date.isoformat(),
            status="Open",
        )
        db.add(ncr)
        db.flush()
        summary["created"].append(f"NCR {ncr.id} on project {DELAYED_PROJECT_ID} (supplier {HIGH_RISK_SUPPLIER_ID})")
    else:
        summary["already_present"].append(f"NCR on project {DELAYED_PROJECT_ID}")

    return summary


DEMO_GUIDE_TEMPLATE = """\
# Demo Guide

Generated by `backend/scripts/seed_demo_data.py`. Re-run that script any
time -- it's idempotent and will not duplicate rows.

## The 3 anchor projects

| Role | Project ID | Name | Status |
|---|---|---|---|
| Healthy | {healthy_id} | {healthy_name} | {healthy_status} |
| Delayed, supplier issues | {delayed_id} | {delayed_name} | {delayed_status} |
| At-risk, safety | {safety_id} | {safety_name} | {safety_status} |

## Suppliers to demo

| Supplier ID | Name | Expected risk |
|---|---|---|
| {high_risk_id} | {high_risk_name} | **High** (~70-80) -- chronic late delivery + open NCRs |
| {medium_risk_id} | {medium_risk_name} | **Medium** (~55-65) -- some delay/quality issues, not chronic |
| {low_risk_id} | {low_risk_name} | **Low/Medium** -- cleanest delivery + NCR record available |

## Step 1 -- Meeting Intelligence

`POST /agents/meeting_intelligence`

```json
{{
  "input": {{
    "notes": "{meeting_notes_escaped}"
  }}
}}
```

Or reference the seeded meeting directly (this reconstructs notes from the
decision on file, which is less rich than the full narrative above but
still produces a real decision + action item):

```json
{{
  "input": {{
    "meeting_id": {meeting_id}
  }}
}}
```

Expect: a decision about switching suppliers, a risk about the schedule
slip, and an action item owned by the Procurement Lead.

## Step 2 -- Supplier Risk

`POST /agents/supplier_risk`

```json
{{
  "input": {{
    "supplier_id": {high_risk_id}
  }}
}}
```

Expect: `overall_severity: "high"`, concerns citing real delay days and NCR
counts, a risk_score in the 70-80 range.

Repeat with `"supplier_id": {low_risk_id}` for contrast -- expect a
noticeably lower risk_score and `overall_severity` of "low" or "medium".

## Step 3 -- Executive Report

`POST /agents/executive_report`

```json
{{
  "input": {{}}
}}
```

Expect: project {delayed_id} appears in "Projects at Risk" (Delayed status
+ the seeded NCR), a Supplier Concerns section that deep-dives supplier
{high_risk_id} via the supplier_risk subagent, and a coherent
recommendation to address the rebar delay.

## Step 4 -- Chat routing (optional, ties it together)

`POST /chat`

```json
{{"message": "How risky is supplier {high_risk_id}?"}}
```

```json
{{"message": "Give me this week's status update"}}
```
"""


def write_demo_guide(db, meeting_id: int) -> Path:
    healthy = db.get(Project, HEALTHY_PROJECT_ID)
    delayed = db.get(Project, DELAYED_PROJECT_ID)
    safety = db.get(Project, SAFETY_RISK_PROJECT_ID)
    high = db.get(Supplier, HIGH_RISK_SUPPLIER_ID)
    medium = db.get(Supplier, MEDIUM_RISK_SUPPLIER_ID)
    low = db.get(Supplier, LOW_RISK_SUPPLIER_ID)

    content = DEMO_GUIDE_TEMPLATE.format(
        healthy_id=healthy.id, healthy_name=healthy.project_name, healthy_status=healthy.status,
        delayed_id=delayed.id, delayed_name=delayed.project_name, delayed_status=delayed.status,
        safety_id=safety.id, safety_name=safety.project_name, safety_status=safety.status,
        high_risk_id=high.id, high_risk_name=high.supplier_name,
        medium_risk_id=medium.id, medium_risk_name=medium.supplier_name,
        low_risk_id=low.id, low_risk_name=low.supplier_name,
        meeting_id=meeting_id,
        meeting_notes_escaped=DEMO_MEETING_NOTES.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n"),
    )

    # Written under scripts/ (volume-mounted to backend/scripts/ on the
    # host) rather than the true repo root: the container only has
    # backend/{app,alembic,scripts,tests} mounted, nothing above that. The
    # caller is expected to move this to the repo root on the host side.
    guide_path = Path(__file__).resolve().parent / "DEMO_GUIDE.md"
    guide_path.write_text(content, encoding="utf-8")
    return guide_path


def main() -> None:
    with SessionLocal() as db:
        summary = seed(db)
        db.commit()
        guide_path = write_demo_guide(db, meeting_id=summary["meeting_id"])

    print("Created:", summary["created"] or "(nothing new)")
    print("Already present:", summary["already_present"] or "(none)")
    print(f"Wrote {guide_path}")


if __name__ == "__main__":
    main()
