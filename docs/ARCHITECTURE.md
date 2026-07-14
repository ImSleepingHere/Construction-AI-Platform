# Architecture

## System overview

```
                                   ┌─────────────────────┐
                                   │   Swagger UI / curl  │
                                   └──────────┬───────────┘
                                              │ HTTP
                                   ┌──────────▼───────────┐
                                   │   FastAPI (main.py)  │
                                   │  agents / chat / approvals │
                                   │  metrics / projects / suppliers │
                                   └──────────┬───────────┘
                                              │
                      ┌───────────────────────┼───────────────────────┐
                      │                       │                       │
             ┌────────▼────────┐   ┌──────────▼──────────┐  ┌────────▼────────┐
             │  Agent Registry  │   │   Intent Router      │  │   APScheduler   │
             │  (auto-discovery)│   │  (/chat classifier)  │  │  (cron -> agent │
             └────────┬─────────┘   └──────────┬───────────┘  │      .run())    │
                      │                        │              └────────┬────────┘
        ┌─────────────┼────────────┬───────────┘                      │
        │             │            │                                  │
┌───────▼──────┐┌─────▼──────┐┌────▼─────────────┐                    │
│meeting_       ││supplier_   ││executive_report   │◄───────────────────┘
│intelligence   ││risk        ││ (calls supplier_  │
│(single-turn)  ││(tool-calling)││ risk as subagent)│
└───────┬───────┘└─────┬──────┘└────────┬──────────┘
        │              │                │
        └──────────────┼────────────────┘
                        │  BaseAgent.run()
              ┌─────────▼──────────┐
              │   LLMClient         │────► Gemini API (generate, embed)
              │  (GeminiClient)     │
              └─────────┬───────────┘
                        │
              ┌─────────▼──────────┐        ┌───────────────────┐
              │   Tool Registry     │───────►│  domain tools      │
              │  (@tool decorator)  │        │  (query dataset)   │
              └─────────┬───────────┘        └─────────┬──────────┘
                        │                               │
              ┌─────────▼───────────────────────────────▼──────────┐
              │                   PostgreSQL 16 + pgvector          │
              │  18 dataset tables      4 AI-layer tables           │
              │  (projects, POs,        (ai_memories, ai_audit_logs,│
              │   suppliers, NCRs...)    approval_requests,         │
              │                          document_chunks)           │
              └───────────────────────────────────────────────────┘
```

Every request that touches an LLM goes through exactly one chokepoint —
`LLMClient` — regardless of whether it originates from an agent, the chat
router, or a cron job. Every LLM call, successful or not, is written to
`ai_audit_logs` before the caller ever sees a response.

## Agent framework design

The framework (`backend/app/agents/`) is a small, from-scratch layer built
around four concepts:

**Skills.** Every agent is a folder containing `SKILL.md` (YAML frontmatter +
a Markdown system prompt) and `agent.py`. `skills.py` parses the frontmatter
into a typed `Skill` dataclass: `name`, `description`, `version`, `max_turns`,
`tools`, `output_schema`, `grounding`. The Markdown body becomes the system
instruction verbatim — editing the prompt means editing a file, not
redeploying code.

**Tools.** Plain Python functions decorated with `@tool(name=..., description=...)`
(`tools.py`). The decorator introspects the function's type hints to build a
JSON Schema automatically (uppercased, per Gemini's function-declaration
format) and registers the function in a global `ToolRegistry`. A tool's
first parameter is always `db: Session`, injected by the framework — the LLM
never sees or controls it. Every domain tool (`supplier_risk/tools.py`,
`executive_report/tools.py`) queries the dataset directly; none of them
mutate it.

**The run loop.** `BaseAgent.run()` (`base.py`) is the only way an agent
executes. It builds the prompt via the agent's `prepare_input`, then routes
to one of two modes based on whether the skill declares tools:

- *Single-turn*: one `LLMClient.generate()` call with `response_schema` set
  to the agent's Pydantic output model. Used by `meeting_intelligence`.
- *Tool-calling loop*: up to `max_turns` iterations of (LLM emits a tool
  call → framework executes it → result fed back into the conversation),
  ending in a schema-constrained final turn. Used by `supplier_risk`,
  `executive_report`, and `hello_world`.

Every run writes exactly one row to `ai_audit_logs` (workflow, prompt,
system instruction, raw output, `output_valid`, token counts, latency,
and a `metadata_json` blob carrying the full `tool_call_trace`) — whether
it succeeds, fails validation, or errors outright. On success, `on_success`
hooks let an agent persist structured facts to `ai_memories` via
`ctx.store_memory(...)`.

**Subagents.** After discovery, `registry.py` also registers every agent as
a callable tool under its own skill name — any agent can list another
agent's name in its `tools:` frontmatter and invoke it mid-loop
(`executive_report` calls `supplier_risk` this way to deep-dive a specific
supplier). Two guards prevent runaway recursion: a shared `call_budget`
(default 20 LLM calls, decremented before every call and propagated back
from subagent to parent) and a `max_depth` (default 2), enforced before a
subagent is even invoked.

**Cron.** `services/scheduler.py` wraps APScheduler's `BackgroundScheduler`.
`register_agent_cron(skill_name, cron_expr, input_payload)` schedules a
plain `get_agent(skill_name).run(db, input_payload)` call on its own fresh
DB session. `executive_report` runs every Monday 09:00 UTC; the same code
path is reachable on demand via `POST /agents/executive_report`.

## Data model

**18 dataset tables** (SQLite → Postgres import, FKs intentionally stripped
— relationships live at the SQLAlchemy layer, not enforced by the DB):
`projects`, `suppliers`, `purchase_requests`, `purchase_orders`, `meetings`,
`project_decisions`, `ncrs`, `safety_events`, `generated_documents`,
`subcontractors`, `subcontractor_evaluations`, `daily_activities`,
`site_reports`, `correspondence`, `claims`, `claim_evidence`,
`change_orders`, `documents`. Only the 9 actually used by an agent or tool
are mapped as SQLAlchemy models (`models/construction.py`); the rest exist
in the database but are out of scope for this build.

**4 AI-layer tables** (`models/ai_layer.py`, Alembic-managed):

- `ai_audit_logs` — one row per LLM call, ever. The reproducibility
  backbone: workflow, prompt, system instruction, raw output, validity,
  tokens, latency, and a JSONB `metadata_json` (tool trace, skill version,
  budget/depth for subagent chains).
- `ai_memories` — structured facts an agent chose to remember
  (`category`, `content`, `confidence`, `source_reference`, optional
  `project_id`), each with a `vector(768)` embedding for semantic recall.
- `document_chunks` — chunked + embedded `generated_documents` (emails,
  site reports, meeting minutes, claim threads), also `vector(768)`, for
  `search_documents`.
- `approval_requests` — a human-in-the-loop queue for actions that should
  require review before executing. Modeled and exposed read-only
  (`GET /approvals`); nothing currently writes to it, since no agent in
  this build performs an action consequential enough to require it —
  it's plumbing for a future write-capable workflow.

## Design decisions

**A custom agent framework, not an existing library.** Beyond avoiding a
new dependency mid-build, the actual reason is that this SDK version
(`google-genai==0.3.0`) has real, specific brokenness — no `ThinkingConfig`,
a `response_schema` auto-converter that silently mangles nested models, no
`additionalProperties` equivalent — that a general-purpose framework would
paper over or fight. Owning the ~500-line core (`base.py` + `tools.py` +
`skills.py`) meant every one of those quirks got fixed once, at the root,
instead of worked around per-agent.

**Gemini.** Chosen up front (project constraint), not re-litigated here —
but worth noting the build surfaced two real SDK-version bugs (below) that
a newer SDK likely doesn't have. The fixes are isolated to `llm_client.py`;
swapping providers means implementing `LLMClient`, nothing else changes.

**pgvector, not a separate vector store.** One database for structured
dataset queries (`purchase_orders`, `ncrs`, ...) and vector search
(`document_chunks`, `ai_memories`) means a single connection pool, one
backup story, and SQL joins between the two when useful (e.g. filtering
`document_chunks` by `project_id`). At this data scale (~1,060 document
chunks, ~30 memories) an ANN index would be premature; plain
`cosine_distance` sequential scans are fast enough.

**Synchronous, not async.** FastAPI supports both; every I/O path here
(Postgres via psycopg3, Gemini via the SDK's sync client) is synchronous,
and the whole system runs single-worker on a laptop for a capstone demo —
there's no concurrent-request load to justify the complexity of threading
async through the agent loop, tool functions, and SQLAlchemy sessions.

**Single-tenant, no auth.** Nothing in this build distinguishes users or
restricts access — deliberately, for this phase. It's a local demo of the
agent framework and data layer, not a deployed multi-tenant product; adding
auth now would be effort spent on a concern the capstone doesn't evaluate,
at the cost of every endpoint needing it threaded through.

## Two framework bugs caught and fixed during build

**1. `thought_signature` on Gemini 3.x tool calls.** Multi-turn tool-calling
failed on turn 2 with `Function call is missing a thought_signature`.
Gemini 3.x thinking models require echoing a `thought_signature` on
function-call parts, which needs a `thinking_config` the installed SDK
(`0.3.0`) doesn't expose at all. Fix: switched `GEMINI_MODEL` to
`gemini-2.5-flash-lite`, which isn't a Gemini 3.x thinking model and
doesn't have the requirement. (`llm_client.py`, `.env`)

**2. `response_schema` silently broken for realistic schemas.** Passing a
Pydantic model with nested models or `Optional` fields as `response_schema`
either crashed (`AttributeError: 'dict' object has no attribute 'upper'`)
or, worse, silently returned wrong output (a free-form `dict` field always
came back `{}`). Root cause: the SDK's `t_schema()` calls
`.model_json_schema()` on anything that isn't a plain `dict` — including a
`genai_types.Schema` *instance*, since `Schema` is itself a Pydantic model,
which re-triggers the exact broken auto-conversion being worked around.
Fix: `pydantic_to_gemini_schema()` hand-builds a plain dict schema
(inlining nested models, converting `Optional[X]` to `nullable: true`,
stringifying `minLength`/`maxLength`), bypassing the SDK's conversion
entirely. (`llm_client.py`)

A related, non-bug consequence of (2): this schema format has no
`additionalProperties` equivalent, so any field that was going to be a
free-form `dict` (e.g. `WeeklyReport.supporting_data`) is instead
`list[str]` of `"label: value"` strings.

## Rubric alignment

**AI Agent Quality (20%)** — `agents/{meeting_intelligence,supplier_risk,
executive_report}/` (3 distinct agent patterns: single-turn, tool-calling,
tool-calling-with-subagents); `agents/base.py` (budget/depth caps, audit
logging, structured-output validation on every run); `agents/registry.py`
(subagent invocation); `services/scheduler.py` (autonomous cron trigger);
`api/chat.py` + `services/intent_router.py` (intent-based routing across
agents); `tests/test_base_agent.py` (budget exhaustion, depth caps, tool
ordering verified under test, not just by hand).

**Backend Architecture (20%)** — `agents/tools.py` + `agents/skills.py`
(declarative, config-driven agent definition — no per-agent boilerplate
beyond `prepare_input`/`on_success`); `api/` (7 route modules, consistent
`Depends(get_db)` pattern); `services/llm_client.py` (single point of
integration with the LLM provider, swappable via the `LLMClient` ABC);
`tests/conftest.py` (SAVEPOINT-isolated test sessions against the real DB,
no separate test-DB infrastructure needed).

**Database Design (15%)** — `models/ai_layer.py` (4-table AI layer:
audit trail, semantic memory, document chunks, approval queue, each with a
clear single responsibility); `models/construction.py` (SQLAlchemy mapping
over the 9 dataset tables actually used, deliberately not enforcing FKs the
source data doesn't have); `alembic/versions/` (both migrations hand-pruned
to their actual intent, with the reasoning for every stripped autogenerate
line documented in the migration file itself).

**Business Understanding (15%)** — the 5 `supplier_risk` domain tools and 5
`executive_report` domain tools map directly to real construction PM
concerns (on-time delivery rate, NCR status, safety severity, projects at
risk) rather than generic CRUD; `DEMO_GUIDE.md` + `scripts/seed_demo_data.py`
demonstrate the platform against a coherent, verifiable narrative instead of
random rows; `NOTES.md`'s data-quirk entries (e.g. anchoring "recent" to
each table's own max date, not wall-clock time) reflect actually
understanding what the data represents, not just querying it.
