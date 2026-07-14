# Construction AI Platform

An AI agent framework for construction project management: three
Gemini-powered agents (meeting intelligence, supplier risk analysis,
executive weekly reporting) that ground every claim in real project data
via tool-calling, hybrid semantic search, and a full audit trail. Capstone
project.

## Stack

- **Backend:** FastAPI + Python 3.12
- **Database:** PostgreSQL 16 with pgvector
- **Cache:** Redis 7
- **LLM Provider:** Google Gemini (swappable)

## Getting started

Prerequisites: Docker Desktop, Python 3 (for `scripts/verify_setup.py` only
— everything else runs in Docker), Git.

```bash
# 1. Clone and enter the repo
git clone <this-repo-url>
cd Construction-AI-Platform

# 2. Configure environment
cp .env.example .env
# edit .env: fill in GEMINI_API_KEY, set APP_SECRET_KEY to any long random string

# 3. Start Postgres, Redis, and the API
docker compose up -d --build

# 4. Load the dataset (18 tables, ~13,400 rows)
docker exec -i construction_ai_postgres psql -U construction_ai -d construction_ai \
  < data/construction_ai_dataset_postgres.sql

# 5. Fix sequence drift left by the bulk SQL import (see data/fix_sequences.sql --
#    without this, any future insert into a dataset table fails with a
#    UniqueViolation)
docker exec -i construction_ai_postgres psql -U construction_ai -d construction_ai \
  < data/fix_sequences.sql

# 6. Run migrations for the AI-layer tables (ai_memories, ai_audit_logs,
#    approval_requests, document_chunks) + enable pgvector
docker exec -e PYTHONPATH=/app construction_ai_api alembic upgrade head

# 7. Ingest generated_documents into document_chunks (emails/reports/minutes
#    -> chunked + embedded). Takes 15-30 minutes for the full 1,060 docs.
docker exec -e PYTHONPATH=/app construction_ai_api python /app/scripts/ingest_documents.py --all

# 8. Seed the curated demo narrative (3 anchor projects/suppliers) and
#    generate DEMO_GUIDE.md
docker exec -e PYTHONPATH=/app construction_ai_api python /app/scripts/seed_demo_data.py
mv backend/scripts/DEMO_GUIDE.md DEMO_GUIDE.md

# 9. Verify everything actually works
python scripts/verify_setup.py

# 10. Open the API
open http://localhost:8000/docs   # or just visit it in a browser
```

Steps 4-8 are one-time setup (idempotent to re-run, except step 7 which
skips already-ingested documents rather than re-embedding them). After
that, `docker compose up -d` / `make dev` is all you need day to day.

Follow [DEMO_GUIDE.md](DEMO_GUIDE.md) for a guided walkthrough with real
project/supplier ids once setup is done.

### Frontend

A Next.js frontend lives in `frontend/` and talks to the API above. With
the backend running:

```bash
docker compose up -d --build frontend
```

Then open [http://localhost:3000](http://localhost:3000). See
[frontend/README.md](frontend/README.md) for the page inventory, dev
commands, and conventions.


## Project Structure:

construction-ai-platform/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── api/
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   └── config.py
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── agents/
│   │   └── memory/
│   ├── alembic/
│   ├── tests/
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/          # routes (App Router)
│   │   ├── components/
│   │   └── lib/          # api.ts (typed client), types.ts, format.ts
│   └── Dockerfile
├── data/
├── docker/
├── scripts/
├── .env.example
├── .gitignore
├── docker-compose.yml
└── README.md

## Focus workflows (this build)

- Meeting Intelligence
- Supplier Risk Analysis
- Executive Weekly Report

## Documentation

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — system design, agent
  framework internals, data model, design decisions, rubric alignment
- [docs/API.md](docs/API.md) — endpoint reference with examples
- [DEMO_GUIDE.md](DEMO_GUIDE.md) — curated demo walkthrough with real
  project/supplier ids and copy-pasteable request bodies
- [NOTES.md](NOTES.md) — development gotchas and environment quirks

## Adding a new agent

Every agent lives in its own folder under `backend/app/agents/<skill_name>/`
and is auto-discovered by `backend/app/agents/registry.py` — no manual
wiring needed. A folder counts as an agent if it contains both `SKILL.md`
and `agent.py`.

**`backend/app/agents/hello_world/` is the canonical reference agent.** It
demonstrates the full pattern:

- `SKILL.md` — YAML frontmatter (name, description, version, max_turns,
  tools, output_schema, grounding) + a Markdown system prompt as the body
- `schemas.py` — the Pydantic output model (`HelloOutput`). Avoid
  `Optional[...] = None` fields in output schemas — this SDK version's
  structured-output mode rejects `null` in the generated JSON Schema; use
  `list[int] = Field(default_factory=list)` instead
- `agent.py` — a `BaseAgent` subclass implementing `prepare_input` (build the
  prompt from `ctx.input`) and optionally `on_success` (persist memories via
  `ctx.store_memory(...)`)

Once the folder exists, the agent is live at `POST /agents/<skill_name>`
(body: `{"input": {...}}`) and listed at `GET /agents` — no route or import
to add by hand. Copy the `hello_world` folder as your starting point.