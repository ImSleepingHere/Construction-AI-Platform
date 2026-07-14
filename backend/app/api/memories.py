"""Read-only access to ai_memories (structured facts agents chose to remember).

`search` is a plain ILIKE on content -- e.g. `?category=risk_assessment&search=Supplier
054` to find prior risk assessments mentioning a given supplier by name, since
memories don't have a dedicated supplier_id column (content is free text).
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.ai_layer import AIMemory
from app.schemas.memories import AIMemoryPage, AIMemoryRead

router = APIRouter(prefix="/memories", tags=["memories"])


@router.get("", response_model=AIMemoryPage)
def list_memories(
    category: Optional[str] = None,
    project_id: Optional[int] = None,
    search: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
) -> AIMemoryPage:
    limit = max(1, min(limit, 100))
    offset = max(0, offset)

    q = db.query(AIMemory)
    if category:
        q = q.filter(AIMemory.category == category)
    if project_id is not None:
        q = q.filter(AIMemory.project_id == project_id)
    if search:
        q = q.filter(AIMemory.content.ilike(f"%{search}%"))

    total = q.count()
    rows = q.order_by(AIMemory.created_at.desc()).offset(offset).limit(limit).all()

    return AIMemoryPage(
        items=[AIMemoryRead.model_validate(r) for r in rows],
        total=total,
        limit=limit,
        offset=offset,
    )
