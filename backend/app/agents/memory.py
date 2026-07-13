"""Memory tools exposed to agents.

Two operations agents can perform on the ai_memories table via the tool
registry:

- search_memory: keyword-based retrieval with optional project/category filters.
  For now this uses ILIKE on content. Once document ingestion is live and we
  have embeddings on memories, this upgrades to hybrid semantic + keyword.
- store_memory: write a memory row from within an agent's tool-calling loop.

Both are exposed as @tool-decorated functions and get auto-registered.
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.agents.tools import tool
from app.models.ai_layer import AIMemory


VALID_CATEGORIES = {
    "decision",
    "risk",
    "action_item",
    "lesson_learned",
    "blocker",
    "insight",
    "risk_assessment",
    "trivia_answer",  # smoke test
}


@tool(
    name="search_memory",
    description=(
        "Search the AI memory store for relevant prior facts. Returns a list of "
        "matching memories with id, category, content, confidence, and creation "
        "date. Use this before making claims to check what the system already "
        "knows. Empty results = no matching prior context; do not treat as "
        "positive evidence of absence."
    ),
)
def search_memory(
    db: Session,
    query: str,
    project_id: Optional[int] = None,
    category: Optional[str] = None,
    limit: int = 10,
) -> list[dict]:
    """Keyword search over ai_memories.content, with optional filters.

    Args:
        query: Text to match against memory content. Case-insensitive substring.
        project_id: If provided, restrict to memories linked to this project.
        category: If provided, restrict to a single memory category.
        limit: Max number of results (1-50).
    """
    limit = max(1, min(int(limit), 50))

    q = db.query(AIMemory)

    if query and query.strip():
        # Simple ILIKE match. Splitting on whitespace lets multi-word queries
        # match memories that contain any of the terms.
        terms = [t for t in query.strip().split() if t]
        if terms:
            q = q.filter(
                or_(*[AIMemory.content.ilike(f"%{t}%") for t in terms])
            )

    if project_id is not None:
        q = q.filter(AIMemory.project_id == project_id)

    if category:
        q = q.filter(AIMemory.category == category)

    rows = q.order_by(AIMemory.created_at.desc()).limit(limit).all()

    return [
        {
            "id": r.id,
            "category": r.category,
            "content": r.content,
            "confidence": round(r.confidence, 2),
            "project_id": r.project_id,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


@tool(
    name="store_memory",
    description=(
        "Store a new memory in the AI memory store. Use this mid-loop to "
        "record a fact you just learned that future agent runs should be "
        "able to retrieve. The content should be a single self-contained "
        "sentence — memories are retrieved individually, not as a thread."
    ),
)
def store_memory(
    db: Session,
    category: str,
    content: str,
    confidence: float = 0.7,
    project_id: Optional[int] = None,
) -> dict:
    """Insert a memory row and return its id.

    Args:
        category: One of the recognized categories (decision, risk, action_item,
                  lesson_learned, blocker, insight, risk_assessment).
        content: A single self-contained sentence describing the fact.
        confidence: 0.0-1.0. Reflects how sure the caller is.
        project_id: Optional project scope.
    """
    if not category or category not in VALID_CATEGORIES:
        return {
            "error": f"unknown category {category!r}",
            "valid_categories": sorted(VALID_CATEGORIES),
        }
    if not content or not content.strip():
        return {"error": "content must not be empty"}

    confidence = max(0.0, min(float(confidence), 1.0))

    row = AIMemory(
        project_id=project_id,
        category=category,
        content=content.strip(),
        source_reference={"type": "tool_call", "tool": "store_memory"},
        confidence=confidence,
        extracted_by="tool_call",
    )
    db.add(row)
    db.flush()
    return {
        "id": row.id,
        "category": row.category,
        "content": row.content,
        "confidence": row.confidence,
        "project_id": row.project_id,
    }