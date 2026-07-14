# API Reference

Base URL (local): `http://localhost:8000`. Interactive docs (Swagger UI):
`http://localhost:8000/docs`. This is a hand-written overview of what each
endpoint group is *for* — see Swagger for exhaustive schema detail.

## Health

**`GET /health`** — Liveness/readiness check. Returns environment and LLM
provider, no DB access. Use this to confirm the container is up before
anything else.

```bash
curl http://localhost:8000/health
# {"status":"ok","env":"development","llm_provider":"gemini"}
```

## Agents

The core of the platform. Every agent (`meeting_intelligence`,
`supplier_risk`, `executive_report`, and the reference agent `hello_world`)
is auto-discovered from `backend/app/agents/` and exposed through the same
two routes — adding a new agent never means adding a new route.

**`GET /agents`** — List every registered agent (name, description,
version).

```bash
curl http://localhost:8000/agents
```

**`POST /agents/{skill_name}`** — Run an agent synchronously. See
[Agent invocation protocol](#agent-invocation-protocol) below for the exact
request/response shape.

```bash
curl -X POST http://localhost:8000/agents/supplier_risk \
  -H "Content-Type: application/json" \
  -d '{"input": {"supplier_id": 1}}'
```

Use this when you already know which agent you want. For "I don't know
which agent handles this," use `/chat` instead.

## Chat

**`POST /chat`** — Free-text entry point. An intent classifier (one LLM
call) decides which of the 3 domain agents should handle the message (or
answers directly if none apply), extracts what that agent needs from the
message, and runs it.

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "How risky is supplier 42?"}'
```

Response:

```json
{
  "agent_used": "supplier_risk",
  "response": { "supplier_id": 42, "risk_score": 70, "...": "..." },
  "audit_log_id": 45,
  "latency_ms": 9734
}
```

`agent_used` is `null` when no agent applies — `response` is then a plain
string answer, not a structured object. Use `/chat` for a conversational
frontend; use `/agents/{skill_name}` directly when you're building
something that always calls the same agent (no need to pay for a
classification call every time).

## Approvals

**`GET /approvals`** — Paginated list of the human-in-the-loop approval
queue (`?status=pending&limit=20&offset=0`). Read-only: nothing currently
writes to this queue (see [ARCHITECTURE.md](ARCHITECTURE.md)), but the
model and endpoint are live for a future write-capable workflow.

```bash
curl "http://localhost:8000/approvals?limit=5"
# {"items": [], "total": 0, "limit": 5, "offset": 0}
```

**`GET /approvals/{id}`** — Single approval request by id. 404 if missing.

## Metrics

Observability for demos and evaluators — all three are SQL aggregates over
`ai_audit_logs`/`ai_memories`, cheap regardless of table size.

**`GET /metrics/agents`** — Per-workflow: total runs, success rate, avg
latency, avg tokens, last run timestamp.

**`GET /metrics/tools`** — Per-tool: total invocations, avg output size
(chars), error rate. Includes subagent invocations (they're tool calls
too).

**`GET /metrics/overview`** — Total LLM calls, total tokens, a rough cost
estimate, and row counts for `ai_audit_logs`/`ai_memories`/`document_chunks`.

```bash
curl http://localhost:8000/metrics/overview
```

## Projects / Suppliers

Thin read-only views over the dataset, independent of the agent layer —
useful for a frontend to populate dropdowns or look up a name before
calling an agent by id.

**`GET /projects`** / **`GET /projects/{id}`** — `?limit=&offset=`
pagination on the list; 404 on missing id.

**`GET /suppliers`** — `?limit=&offset=` pagination.

```bash
curl "http://localhost:8000/projects?limit=3"
curl http://localhost:8000/projects/1
curl "http://localhost:8000/suppliers?limit=3"
```

## Debug (not for the demo)

**`POST /debug/generate`** — Raw passthrough to the LLM client, no agent
framework involved. Exists purely for verifying LLM wiring during
development. Not part of the platform's actual surface — see `ai_debug.py`'s
module docstring.

---

## Agent invocation protocol

Every agent, regardless of internal complexity, is invoked identically:

**Request**

```json
POST /agents/{skill_name}
{
  "input": { "...": "whatever fields that specific agent expects" }
}
```

`input` is agent-specific — `meeting_intelligence` wants `notes` or
`meeting_id`; `supplier_risk` wants `supplier_id`; `executive_report` wants
nothing (`{}`) or an optional `week_of`. See each agent's `SKILL.md` or
`schemas.py` for its exact expected fields, or `DEMO_GUIDE.md` for
copy-pasteable examples against real seeded data.

**Response** — the agent's structured output fields, flattened to the top
level, plus fixed metadata fields present on every response regardless of
agent:

| Field | Type | Meaning |
|---|---|---|
| *(agent-specific fields)* | varies | The agent's own output schema, spread at the top level |
| `audit_log_id` | int | Row id in `ai_audit_logs` for this run — the full prompt/response/trace |
| `model` | string | Which model actually served the request |
| `latency_ms` | int | Wall-clock time for the whole run (all turns) |
| `turns_used` | int | How many LLM calls the tool-calling loop took (0/1 for single-turn agents) |
| `tool_call_trace` | array | Every tool call made, in order, with arguments and output |
| `memory_ids` | array | Row ids written to `ai_memories` by this run, if any |
| `output_valid` | bool | Whether the LLM's output validated against the agent's schema |
| `error` | string \| null | Set when `output_valid` is false, or the run failed outright |

A run can fail gracefully (`output_valid: false`, `error` set, HTTP 200 —
the *request* succeeded, the *agent's output* just didn't validate) or
fail hard (HTTP 404 for an unknown `skill_name`, HTTP 422 for a malformed
request body). `audit_log_id` is always present, even on a failed run —
every attempt is logged.
