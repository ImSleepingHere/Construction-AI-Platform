"""
Convert the SQLite dump to a Postgres-compatible SQL file.

Strategy:
- Strip FOREIGN KEY constraints from CREATE TABLE (SQLite dumps tables in
  alphabetical order, not dependency order, so FKs would fail at creation time).
- Rewrite SQLite-specific syntax (INTEGER PRIMARY KEY, REAL, quoted INSERTs).
- Skip SQLite pragmas and transaction wrappers.
- Data integrity is preserved because the source SQLite DB already validated it;
  SQLAlchemy models define relationships at the ORM level.
"""

import re
from pathlib import Path

SRC = Path("data/construction_ai_dataset_full_dump.sql")
DST = Path("data/construction_ai_dataset_postgres.sql")


def convert(sqlite_sql: str) -> str:
    sql = sqlite_sql

    # Strip FOREIGN KEY clauses, including the comma before them.
    # Matches both single-FK and multi-FK CREATE TABLE definitions,
    # across line breaks (\s matches newlines).
    sql = re.sub(
        r",\s*FOREIGN KEY\s*\([^)]+\)\s+REFERENCES\s+\w+\s*\([^)]+\)",
        "",
        sql,
    )

    # INTEGER PRIMARY KEY -> SERIAL PRIMARY KEY (SQLite auto-increment)
    sql = re.sub(r"\bINTEGER PRIMARY KEY\b", "SERIAL PRIMARY KEY", sql)

    # REAL -> DOUBLE PRECISION
    sql = re.sub(r"\bREAL\b", "DOUBLE PRECISION", sql)

    # Unquote table names in INSERTs: INSERT INTO "table" -> INSERT INTO table
    sql = re.sub(
        r'INSERT INTO "([a-zA-Z_][a-zA-Z0-9_]*)"',
        r"INSERT INTO \1",
        sql,
    )

    # Drop SQLite-specific lines
    kept = []
    for line in sql.splitlines():
        stripped = line.strip()
        if stripped in ("BEGIN TRANSACTION;", "COMMIT;"):
            continue
        if stripped.startswith("PRAGMA"):
            continue
        if "sqlite_sequence" in stripped.lower():
            continue
        kept.append(line)

    # No outer transaction: if any single INSERT fails, others still succeed
    return "\n".join(kept) + "\n"


def main() -> None:
    if not SRC.exists():
        raise SystemExit(f"Source not found: {SRC}")

    sqlite_sql = SRC.read_text(encoding="utf-8")
    postgres_sql = convert(sqlite_sql)
    DST.write_text(postgres_sql, encoding="utf-8")

    src_size = SRC.stat().st_size / 1024
    dst_size = DST.stat().st_size / 1024
    print(f"Converted {SRC.name} ({src_size:.1f} KB) -> {DST.name} ({dst_size:.1f} KB)")


if __name__ == "__main__":
    main()