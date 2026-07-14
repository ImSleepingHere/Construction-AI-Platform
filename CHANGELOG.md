# Changelog

Organized by phase, not by commit — see `git log --oneline` for the exact
commit-by-commit history. A few early commit messages are terser than the
rest (`added placeholders for structure`, `meeting intelligence - will be
updated`, `Gemini API call schema debugging`) or mark session boundaries
rather than shipped work (`Claude Code handoff point`, `milestone 3`) —
left as-is per project convention (don't rewrite history, just note it).

## Phase 1-2 — Project skeleton

Docker Compose (Postgres 16 + pgvector, Redis, FastAPI). Dataset loaded (18
tables, ~13,400 rows). First read-only endpoints (`/projects`,
`/suppliers`) to confirm the stack actually works end to end.

## Phase 3.1-3.5 — Agent framework core

- `services/llm_client.py`: `LLMClient` abstraction over Gemini
  (`GeminiClient`), retries, latency/token tracking.
- `agents/tools.py`: `@tool` decorator + `ToolRegistry`, JSON Schema
  auto-derived from type hints.
- `agents/skills.py`: `SKILL.md` loader (YAML frontmatter + Markdown body).
- `agents/base.py`: `BaseAgent`, `AgentContext`, single-turn run loop.
- `agents/memory.py`: `search_memory` / `store_memory` tools.
- Multi-turn tool-calling loop, fixing a real SDK bug along the way
  (`thought_signature` — see ARCHITECTURE.md).
- `agents/registry.py`: auto-discovery + auto-endpoint factory
  (`GET /agents`, `POST /agents/{name}`), subagent invocation with
  shared budget/depth caps.
- `services/scheduler.py`: APScheduler wired into FastAPI startup.
- `agents/hello_world/`: the permanent reference agent for "how do I add
  a new agent."

## Phase 3.6-3.8 — The three domain agents

- **meeting_intelligence** (3.6): migrated from a standalone service onto
  the framework. Single-turn, extracts action items/decisions/risks.
- **supplier_risk** (3.7): 5 domain tools over `purchase_orders`/`ncrs`/
  `suppliers`, multi-turn tool-calling, grounds every risk claim in a real
  tool call result.
- **executive_report** (3.8): 5 more domain tools, calls `supplier_risk` as
  a subagent to deep-dive the most concerning supplier, cron-triggered
  weekly (Mondays 09:00 UTC).

## Phase 4-5 — Document ingestion + hybrid search

- `services/document_ingestion.py`: chunks + embeds all 1,060
  `generated_documents` (emails, site reports, meeting minutes, claim
  threads — mixed Arabic/English) into `document_chunks`.
- `ai_memories.embedding` column (migration, hand-pruned from a very noisy
  autogenerate diff).
- `search_memory` upgraded to hybrid semantic + keyword (pgvector cosine
  similarity ranked first, keyword ILIKE fills in behind).
- `search_documents` tool: semantic search over ingested documents.

Along the way: `GEMINI_EMBEDDING_MODEL` switched from `text-embedding-004`
(no longer exists for this API/account) to `gemini-embedding-001` with
`output_dimensionality=768`.

## Phase 7 — Test suite, chat routing, demo data, docs, submission polish

- **7.1**: pytest suite (24 tests: tools, skills, base agent, endpoints,
  memory). `GET/GET-by-id /approvals` added (was referenced as built but
  wasn't). `Makefile`.
- **7.2**: `POST /chat` — free-text routing to the right agent via a
  one-call intent classifier (`services/intent_router.py`).
- **7.3**: `scripts/seed_demo_data.py` + `DEMO_GUIDE.md` — a coherent
  3-project demo narrative curated from real (not invented) data. Found and
  fixed a real bug in the process: every dataset table's Postgres sequence
  was stuck at 1 (bulk import never called `setval()`), breaking any insert
  into those tables.
- **7.4**: `GET /metrics/{agents,tools,overview}` — SQL-aggregate
  observability over `ai_audit_logs`/`ai_memories`.
- **7.5**: `docs/ARCHITECTURE.md` + `docs/API.md`.
- **7.6**: Fresh-start dry run (`docker compose down -v` → full rebuild →
  dataset load → migrations → ingestion → seed → verify), proven for real,
  not just documented. `scripts/verify_setup.py`, `docker/README.md`.
  Found and fixed a second real bug: `.gitignore` excluded the entire
  `data/` directory (contradicting its own comment), so the dataset dump
  was never actually committed — a fresh clone would have had nothing to
  load.
- **7.7**: this file, README summary line, dead-code cleanup, secret scan.
