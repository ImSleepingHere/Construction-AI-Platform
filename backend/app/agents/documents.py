"""Document search tool exposed to agents.

Semantic search over document_chunks (ingested generated_documents — emails,
site reports, meeting minutes, claim threads). See
app.services.document_ingestion for how chunks get there.
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.agents.tools import tool
from app.models.ai_layer import DocumentChunk
from app.services.llm_client import get_llm_client


@tool(
    name="search_documents",
    description=(
        "Semantic search over ingested project documents (emails, memos). "
        "Returns matching document chunks with source metadata. Use this "
        "to find quotes, decisions, or context from real communications."
    ),
)
def search_documents(
    db: Session, query: str, project_id: Optional[int] = None, limit: int = 5
) -> list[dict]:
    """Cosine similarity search over document_chunks.embedding.

    Args:
        query: Text to embed and search for.
        project_id: If provided, restrict to chunks linked to this project.
        limit: Max number of results (1-20).
    """
    limit = max(1, min(int(limit), 20))
    query_embedding = get_llm_client().embed(query)

    distance = DocumentChunk.embedding.cosine_distance(query_embedding)
    q = db.query(DocumentChunk, distance.label("distance"))
    if project_id is not None:
        q = q.filter(DocumentChunk.project_id == project_id)
    rows = q.order_by(distance).limit(limit).all()

    return [
        {
            "source_type": chunk.source_type,
            "source_id": chunk.source_id,
            "project_id": chunk.project_id,
            "content": chunk.content,
            "similarity_score": round(1 - dist, 4),
        }
        for chunk, dist in rows
    ]
