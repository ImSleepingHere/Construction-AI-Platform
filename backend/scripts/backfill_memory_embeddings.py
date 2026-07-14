"""CLI: backfill embeddings for ai_memories rows written before the
embedding column existed (or where a prior embed() call failed).

Run inside the API container:
    python /app/scripts/backfill_memory_embeddings.py
"""

from __future__ import annotations

from app.core.database import SessionLocal
from app.models.ai_layer import AIMemory
from app.services.llm_client import get_llm_client


def main() -> None:
    llm = get_llm_client()

    with SessionLocal() as db:
        rows = db.query(AIMemory).filter(AIMemory.embedding.is_(None)).all()
        total = len(rows)
        print(f"{total} memories missing an embedding.")

        done = 0
        failed = 0
        for row in rows:
            try:
                row.embedding = llm.embed(row.content)
                db.commit()
                done += 1
            except Exception as exc:
                db.rollback()
                failed += 1
                print(f"  failed id={row.id}: {exc}")

            if (done + failed) % 20 == 0 or (done + failed) == total:
                print(f"[{done + failed}/{total}] backfilled={done} failed={failed}")

    print(f"Done. backfilled={done} failed={failed}")


if __name__ == "__main__":
    main()
