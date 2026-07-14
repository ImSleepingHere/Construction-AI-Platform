"""Memory tools exposed to agents.

Two operations agents can perform on the ai_memories table via the tool
registry:

- search_memory: hybrid semantic + keyword retrieval with optional
  project/category filters. Semantic hits (pgvector cosine similarity on
  ai_memories.embedding) are ranked first, keyword ILIKE hits fill in behind
  them, deduped by id. Rows with a null embedding (written before the
  embedding column existed, or if an embed() call failed) are simply absent
  from the semantic half and can still surface via keyword matching.
- store_memory: write a memory row from within an agent's tool-calling loop.
  Computes and stores an embedding for the new row.

Both are exposed as @tool-decorated functions and get auto-registered.
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.agents.tools import tool
from app.models.ai_layer import AIMemory
from app.services.llm_client import get_llm_client


VALID_CATEGORIES = {
    "decision",
    "risk",
    "action_item",
    "lesson_learned",
    "blocker",
    "insight",
    "risk_assessment",
    "trivia_answer",  # smoke test
    "hello_greeting",  # hello_world reference agent
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
    use_semantic: bool = True,
) -> list[dict]:
    """Hybrid semantic + keyword search over ai_memories.

    Args:
        query: Text to match. Embedded for semantic search (if use_semantic)
               and split into terms for a case-insensitive substring match.
        project_id: If provided, restrict to memories linked to this project.
        category: If provided, restrict to a single memory category.
        limit: Max number of results (1-50).
        use_semantic: If True (default), run pgvector cosine similarity
               against ai_memories.embedding and rank those hits first.
               Falls back to keyword-only if the embed call fails.
    """
    limit = max(1, min(int(limit), 50))

    semantic_rows: list[AIMemory] = []
    if use_semantic and query and query.strip():
        try:
            query_embedding = get_llm_client().embed(query)
            sq = db.query(AIMemory).filter(AIMemory.embedding.isnot(None))
            if project_id is not None:
                sq = sq.filter(AIMemory.project_id == project_id)
            if category:
                sq = sq.filter(AIMemory.category == category)
            semantic_rows = (
                sq.order_by(AIMemory.embedding.cosine_distance(query_embedding))
                .limit(limit)
                .all()
            )
        except Exception:
            # Degrade to keyword-only rather than fail the whole tool call.
            semantic_rows = []

    kq = db.query(AIMemory)
    if query and query.strip():
        # Simple ILIKE match. Splitting on whitespace lets multi-word queries
        # match memories that contain any of the terms.
        terms = [t for t in query.strip().split() if t]
        if terms:
            kq = kq.filter(
                or_(*[AIMemory.content.ilike(f"%{t}%") for t in terms])
            )
    if project_id is not None:
        kq = kq.filter(AIMemory.project_id == project_id)
    if category:
        kq = kq.filter(AIMemory.category == category)
    keyword_rows = kq.order_by(AIMemory.created_at.desc()).limit(limit).all()

    seen: set[int] = set()
    combined: list[AIMemory] = []
    for r in [*semantic_rows, *keyword_rows]:
        if r.id not in seen:
            seen.add(r.id)
            combined.append(r)
    combined = combined[:limit]

    return [
        {
            "id": r.id,
            "category": r.category,
            "content": r.content,
            "confidence": round(r.confidence, 2),
            "project_id": r.project_id,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in combined
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
    content = content.strip()

    try:
        embedding = get_llm_client().embed(content)
    except Exception:
        # Store without an embedding rather than fail the write; it just
        # won't surface via semantic search until backfilled.
        embedding = None

    row = AIMemory(
        project_id=project_id,
        category=category,
        content=content,
        source_reference={"type": "tool_call", "tool": "store_memory"},
        confidence=confidence,
        extracted_by="tool_call",
        embedding=embedding,
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