#!/usr/bin/env python3
"""Verify a fresh setup of the Construction AI Platform is actually working.

Deliberately stdlib-only (urllib, subprocess, json) and runs from the HOST,
not inside a container: the whole point is to prove a fresh clone works
without assuming the backend's Python dependencies are installed anywhere
except inside Docker. It talks to the API over the published port and shells
out to `docker exec` for checks that need direct DB access.

Usage:
    python scripts/verify_setup.py

Exit code 0 if every check passes, 1 otherwise.
"""

from __future__ import annotations

import json
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
API_BASE = "http://localhost:8000"
POSTGRES_CONTAINER = "construction_ai_postgres"

REQUIRED_ENV_VARS = [
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "POSTGRES_DB",
    "GEMINI_API_KEY",
    "APP_SECRET_KEY",
]

EXPECTED_AGENTS = {"hello_world", "meeting_intelligence", "supplier_risk", "executive_report"}

# (table, minimum expected row count) -- see NOTES.md for the dataset's
# documented sizes. document_chunks/ai_memories come from this platform's
# own ingestion/agent runs, not the raw dataset.
MIN_ROW_COUNTS = [
    ("projects", 60),
    ("suppliers", 80),
    ("purchase_requests", 3000),
    ("purchase_orders", 2550),
    ("meetings", 260),
    ("project_decisions", 535),
    ("ncrs", 700),
    ("generated_documents", 1060),
    ("document_chunks", 1000),
    ("ai_memories", 1),
]

results: list[tuple[str, bool, str]] = []


def check(name: str, passed: bool, detail: str = "") -> None:
    results.append((name, passed, detail))
    mark = "PASS" if passed else "FAIL"
    line = f"[{mark}] {name}"
    if detail:
        line += f" -- {detail}"
    print(line)


def check_env_vars() -> None:
    env_path = REPO_ROOT / ".env"
    if not env_path.exists():
        check("`.env` file exists", False, "copy .env.example to .env and fill it in")
        for var in REQUIRED_ENV_VARS:
            check(f"env var {var} present", False, ".env missing entirely")
        return
    check("`.env` file exists", True)

    values: dict[str, str] = {}
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip()

    for var in REQUIRED_ENV_VARS:
        present = bool(values.get(var))
        check(f"env var {var} present", present)


def _http_get(path: str) -> tuple[int, object]:
    req = urllib.request.Request(API_BASE + path, method="GET")
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))


def _http_post(path: str, body: dict, timeout: int = 60) -> tuple[int, object]:
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        API_BASE + path, data=data, method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))


def check_api_up() -> bool:
    try:
        status, body = _http_get("/health")
        check("API is reachable (GET /health)", status == 200, str(body))
        return status == 200
    except (urllib.error.URLError, TimeoutError) as exc:
        check("API is reachable (GET /health)", False, f"{exc} -- is `docker compose up -d` running?")
        return False


def check_agents_registered() -> None:
    try:
        status, body = _http_get("/agents")
        names = {a["name"] for a in body} if status == 200 else set()
        missing = EXPECTED_AGENTS - names
        check(
            "All 4 agents registered (GET /agents)",
            status == 200 and not missing,
            f"found: {sorted(names)}" if not missing else f"missing: {sorted(missing)}",
        )
    except (urllib.error.URLError, TimeoutError, KeyError, TypeError) as exc:
        check("All 4 agents registered (GET /agents)", False, str(exc))


def check_gemini_api_key_works() -> None:
    try:
        status, body = _http_post(
            "/agents/hello_world", {"input": {"name": "verify_setup"}}, timeout=30
        )
        ok = status == 200 and isinstance(body, dict) and body.get("output_valid") is True
        detail = "" if ok else f"status={status} body={body}"
        check("GEMINI_API_KEY works (real hello_world call)", ok, detail)
    except (urllib.error.URLError, TimeoutError) as exc:
        check("GEMINI_API_KEY works (real hello_world call)", False, str(exc))


def check_row_counts() -> None:
    for table, minimum in MIN_ROW_COUNTS:
        try:
            proc = subprocess.run(
                [
                    "docker", "exec", POSTGRES_CONTAINER,
                    "psql", "-U", "construction_ai", "-d", "construction_ai",
                    "-t", "-c", f"SELECT COUNT(*) FROM {table};",
                ],
                capture_output=True, text=True, timeout=15, check=False,
            )
            count = int(proc.stdout.strip() or -1)
            check(f"{table} has >= {minimum} rows", count >= minimum, f"actual: {count}")
        except (subprocess.SubprocessError, ValueError) as exc:
            check(f"{table} has >= {minimum} rows", False, str(exc))


def main() -> int:
    print(f"Verifying setup from {REPO_ROOT}\n")

    print("-- Environment --")
    check_env_vars()

    print("\n-- API --")
    api_up = check_api_up()
    if api_up:
        check_agents_registered()
        check_gemini_api_key_works()
    else:
        check("All 4 agents registered (GET /agents)", False, "skipped: API not reachable")
        check("GEMINI_API_KEY works (real hello_world call)", False, "skipped: API not reachable")

    print("\n-- Database row counts --")
    check_row_counts()

    total = len(results)
    passed = sum(1 for _, ok, _ in results if ok)
    print(f"\n{passed}/{total} checks passed.")

    if passed < total:
        print("\nFailed checks:")
        for name, ok, detail in results:
            if not ok:
                print(f"  - {name}" + (f" ({detail})" if detail else ""))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
