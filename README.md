# Construction AI Platform

AI-powered construction project management platform. Capstone project.

## Stack

- **Backend:** FastAPI + Python 3.12
- **Database:** PostgreSQL 16 with pgvector
- **Cache:** Redis 7
- **LLM Provider:** Google Gemini (swappable)

## Getting started

Prerequisites: Docker Desktop, Python 3.12, Git.

1. Copy `.env.example` to `.env` and fill in your values (especially `GEMINI_API_KEY`)
2. `docker compose up --build`
3. Open http://localhost:8000/docs


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