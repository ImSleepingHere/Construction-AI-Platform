# Development notes and gotchas

## Environment

- Windows host, Docker Desktop with WSL 2, Ubuntu backend
- Container working directory is `/app`; running scripts via `docker exec`
  needs `-e PYTHONPATH=/app`
- Local Python: 3.11.9 (alembic installed, but NOT the project's other
  dependencies — sqlalchemy/pgvector/psycopg2 are only inside the
  container). Container Python: 3.11-slim.
- `git push` / `git fetch` hang indefinitely in this shell: `credential.helper
  = manager` (Windows Git Credential Manager) tries to open a GUI/browser
  prompt that never resolves non-interactively. `GIT_TERMINAL_PROMPT=0`
  does not help (that only suppresses git's own terminal prompts, not GCM's
  GUI flow). Commit locally as normal; push is done manually by the user.

## Framework quirks

- YAML frontmatter: bare `off`/`on` become booleans. Quote them: `grounding: "off"`.
- Installed `google-genai` SDK is `0.3.0` — very old (latest is 2.11.0+).
  Has **no** `ThinkingConfig`/`thinking_config` at all.
- `GEMINI_MODEL=gemini-2.5-flash-lite` (not gemini-3.1-flash-lite): the 3.x
  thinking models require `thought_signature` on echoed function_call parts,
  which this SDK can't produce. 2.5-flash-lite isn't a thinking model, so
  the requirement doesn't apply. Don't switch back without checking the SDK
  version again.
- `GEMINI_EMBEDDING_MODEL=gemini-embedding-001` (not text-embedding-004,
  which no longer exists for this API/account). Defaults to 3072-dim;
  `GeminiClient.embed()` passes `output_dimensionality=768` to match
  `vector(768)` columns everywhere (`EMBEDDING_DIM` in `ai_layer.py`).
- **`response_schema` must NOT be the raw Pydantic class or a
  `genai_types.Schema` instance.** This SDK's `t_schema()` calls
  `.model_json_schema()` on anything that isn't a plain `dict` — including a
  `Schema` instance, since `Schema` is itself a Pydantic model, which
  re-triggers the broken auto-conversion. Always go through
  `pydantic_to_gemini_schema()` in `llm_client.py`, which hand-builds a
  plain dict (inlines nested models — no `$ref`/`$defs` support; converts
  `Optional[X]` to `nullable: true` — no `anyOf`-with-null support;
  stringifies `minLength`/`maxLength` — this SDK's `Schema.min_length` is
  typed `str`, not `int`).
- Gemini's schema format has **no `additionalProperties` equivalent** — a
  free-form `dict` field always round-trips as an empty `{}` (there's no way
  to tell the model what keys to fill in). Use `list[str]` of `"label:
  value"` strings instead for anything that was going to be an open-ended
  dict.
- Avoid `Optional[X] = None` fields generally where possible; prefer
  `list[T] = Field(default_factory=list)` even when the field is
  conceptually "nullable." (The `nullable: true` fix above makes `Optional`
  technically safe now, but the list-default pattern is still simpler.)
- Gemini function declarations require UPPERCASE JSON Schema type names
  (`STRING`, `OBJECT`) — handled in `tools.py`.
- In `_run_with_tools`: this SDK can't combine `tools` + `response_schema`
  in one call. If the model stops calling tools before the schema-forced
  final turn, that turn's output isn't schema-constrained and its JSON
  shape/escaping can't be trusted (observed: wrong field names, invalid
  `\'` escapes). The framework now forces one schema-only finalize call in
  that case rather than trusting the raw text.
- Every model module must be imported in `backend/app/models/__init__.py`;
  agents rely on `import app.models` to ensure `Base.metadata` is complete.
- Every new tool module must be imported in `backend/app/agents/__init__.py`
  for `@tool` to fire (registration is import-time side effect).
- Subagent tools (other agents callable via the tool registry) are
  auto-registered by `registry.py` after discovery — any agent can declare
  another agent's skill name in its own `tools:` list. Budget (`call_budget`,
  default 20) and depth (`max_depth`, default 2) are shared across the whole
  call tree via `AgentContext`.

## Docker

- `backend/scripts/` and `backend/alembic.ini` are **not** copied into the
  image or volume-mounted by default — only `./app` and `./alembic` are.
  Both were added: `scripts/` gets a live volume mount (like `app/`, so
  scripts hot-reload without a rebuild); `alembic.ini` gets a plain `COPY`
  (static config, no need to live-mount). Without these, `alembic` and
  `python /app/scripts/*.py` don't exist in the container at all — the
  first-ever migration must have been run from the host.
- Changing `.env` requires `docker compose up -d api` (or `--build` if
  Dockerfile changed) — `docker compose restart api` does **not** re-read
  `.env` or pick up a rebuilt image, it just restarts the existing
  container with its already-baked-in env/image.

## Alembic

- Autogenerate compares models to DB. Tables in DB but not modeled get flagged
  for DROP — always review the generated migration before running `upgrade head`.
  In practice this project's autogenerate diffs are ~90% noise: 8 unmodeled
  dataset tables flagged for DROP, every dataset TEXT column flagged for a
  cosmetic ALTER to VARCHAR, and FK constraints proposed for tables where
  they were deliberately stripped on import. Hand-prune to just the intended
  change before showing the diff for approval.
- pgvector extension enable belongs in the migration, not out-of-band.
- Dataset tables (18 of them) are outside Alembic's history — do not touch.

## Data

- Dataset was SQLite; imported to Postgres with FKs stripped. Relationships
  live at the SQLAlchemy layer.
- 60 projects, 3000 purchase requests, 2550 POs, 80 suppliers, 260 meetings,
  535 project decisions, 1060 realistic emails/site reports/meeting
  minutes/claim threads (`generated_documents`, mixed Arabic/English).
- `generated_documents` bodies are short (max ~1068 chars / ~270 tokens) —
  chunking at the standard 500-token/50-overlap size produces exactly 1
  chunk per document (1060 total in `document_chunks`), not thousands. This
  is a property of the data, not a chunker bug.
- Tables were generated with inconsistent max dates relative to each other
  and to wall-clock "now" (NCRs top out ~2025-01, safety_events ~2026-05,
  PO promised_delivery extends into 2026-07+). Any "last N days" query
  anchored to wall-clock `date.today()` will silently return empty results
  for some tables. Anchor "recent" windows to `MAX(date_column)` of the
  table being queried instead — see `executive_report/tools.py::_latest_date`.
- `ncrs` has no `severity` column in this dataset (only `safety_events`
  does). Don't write tool descriptions/prompts that imply NCR severity
  exists.

## Running commands

- Start stack: `docker compose up -d`
- Stop: `docker compose down` (keeps data), `docker compose down -v` (wipes data)
- API logs: `docker compose logs -f api`
- One-off script: `docker exec -it -e PYTHONPATH=/app construction_ai_api python /app/app/<path>`
- CLI script (backend/scripts/): `docker exec -it -e PYTHONPATH=/app construction_ai_api python /app/scripts/<name>.py`
- Postgres shell: `docker exec -it construction_ai_postgres psql -U construction_ai -d construction_ai`
- On Windows/Git Bash, `docker exec`/`docker compose` commands with
  container-side absolute paths need `MSYS_NO_PATHCONV=1` prefixed, or Git
  Bash mangles `/app/...` into a host path.
