"""Chunking and ingestion of generated_documents into document_chunks.

Chunking is character-based (~4 chars per token) rather than a real
tokenizer: tiktoken is not installed in this container, and adding it would
be a new dependency. If tiktoken becomes available later, swap
_approx_token_count and the char-based sizing in chunk_text for a real
tokenizer without changing the function signatures.
"""

from __future__ import annotations

import re
from typing import Optional

from sqlalchemy.orm import Session

from app.models.ai_layer import DocumentChunk
from app.models.construction import GeneratedDocument
from app.services.llm_client import get_llm_client

CHARS_PER_TOKEN = 4
CHUNK_TOKENS = 500
OVERLAP_TOKENS = 50
CHUNK_CHARS = CHUNK_TOKENS * CHARS_PER_TOKEN
OVERLAP_CHARS = OVERLAP_TOKENS * CHARS_PER_TOKEN

SOURCE_TYPE = "generated_document"


def chunk_text(
    text: str, chunk_chars: int = CHUNK_CHARS, overlap_chars: int = OVERLAP_CHARS
) -> list[str]:
    """Split text into overlapping chunks, preferring paragraph boundaries.

    Paragraphs (blank-line-separated) are greedily packed into a chunk until
    it would exceed chunk_chars, then a new chunk starts, seeded with the
    trailing overlap_chars of the previous chunk for continuity. A single
    paragraph longer than chunk_chars is hard-split.
    """
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized:
        return []

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", normalized) if p.strip()]
    if not paragraphs:
        paragraphs = [normalized]

    chunks: list[str] = []
    current = ""

    for para in paragraphs:
        candidate = f"{current}\n\n{para}" if current else para
        if len(candidate) <= chunk_chars:
            current = candidate
            continue

        if current:
            chunks.append(current)
            tail = current[-overlap_chars:] if overlap_chars else ""
            current = f"{tail}\n\n{para}" if tail else para
        else:
            current = para

        while len(current) > chunk_chars:
            chunks.append(current[:chunk_chars])
            current = current[chunk_chars - overlap_chars :]

    if current:
        chunks.append(current)

    return chunks


def _document_text(doc: GeneratedDocument) -> str:
    return "\n".join(
        [
            f"Subject: {doc.subject}",
            f"From: {doc.sender}",
            f"Date: {doc.document_date}",
            "",
            doc.body,
        ]
    )


def ingest_generated_documents(
    db: Session, limit: Optional[int] = None, batch_size: int = 20
) -> dict[str, int]:
    """Chunk and embed generated_documents rows into document_chunks.

    Idempotent: a document already represented in document_chunks (matched by
    source_type/source_id) is skipped. Commits after each document so a
    partial run leaves consistent state and can be safely resumed.
    """
    llm = get_llm_client()

    total_available = db.query(GeneratedDocument.id).count()
    total_to_process = min(limit, total_available) if limit is not None else total_available

    ingested = 0
    skipped = 0
    total_chunks = 0
    processed = 0
    offset = 0

    while processed < total_to_process:
        batch_limit = min(batch_size, total_to_process - processed)
        batch = (
            db.query(GeneratedDocument)
            .order_by(GeneratedDocument.id)
            .offset(offset)
            .limit(batch_limit)
            .all()
        )
        if not batch:
            break

        for doc in batch:
            already_ingested = (
                db.query(DocumentChunk.id)
                .filter(
                    DocumentChunk.source_type == SOURCE_TYPE,
                    DocumentChunk.source_id == doc.id,
                )
                .first()
                is not None
            )

            chunks_created = 0
            if already_ingested:
                skipped += 1
            else:
                pieces = chunk_text(_document_text(doc))
                for idx, content in enumerate(pieces):
                    embedding = llm.embed(content)
                    db.add(
                        DocumentChunk(
                            source_type=SOURCE_TYPE,
                            source_id=doc.id,
                            project_id=doc.project_id,
                            chunk_index=idx,
                            content=content,
                            embedding=embedding,
                            token_count=round(len(content) / CHARS_PER_TOKEN),
                        )
                    )
                db.commit()
                ingested += 1
                chunks_created = len(pieces)
                total_chunks += chunks_created

            processed += 1
            if processed % batch_size == 0 or processed == total_to_process:
                print(
                    f"[{processed}/{total_to_process}] ingested doc_id={doc.id} "
                    f"({chunks_created} chunks)"
                )

        offset += len(batch)

    return {"ingested": ingested, "skipped": skipped, "total_chunks": total_chunks}
