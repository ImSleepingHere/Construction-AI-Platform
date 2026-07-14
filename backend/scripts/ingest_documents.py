"""CLI: ingest generated_documents into document_chunks.

Run inside the API container:
    python /app/scripts/ingest_documents.py --limit 5
    python /app/scripts/ingest_documents.py --all
"""

from __future__ import annotations

import argparse

from app.core.database import SessionLocal
from app.services.document_ingestion import ingest_generated_documents


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ingest generated_documents into document_chunks."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--limit", type=int, help="Ingest at most N documents (for testing).")
    group.add_argument("--all", action="store_true", help="Ingest all documents.")
    args = parser.parse_args()

    limit = None if args.all else args.limit

    with SessionLocal() as db:
        result = ingest_generated_documents(db, limit=limit)

    print(
        f"Done. ingested={result['ingested']} skipped={result['skipped']} "
        f"total_chunks={result['total_chunks']}"
    )


if __name__ == "__main__":
    main()
