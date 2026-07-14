"""Tests for the FastAPI endpoints.

POST /agents/hello_world is a real integration test -- it exercises the
actual live LLMClient wiring end-to-end (matching the project's existing
"verify against the real API" pattern), unlike the mocked unit tests in
test_base_agent.py. It is the only test in this suite that calls Gemini.
"""

from __future__ import annotations

from app.models.ai_layer import AIAuditLog


def test_health_returns_200(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_list_agents_includes_all_four(client):
    resp = client.get("/agents")
    assert resp.status_code == 200
    names = {a["name"] for a in resp.json()}
    assert names == {"hello_world", "meeting_intelligence", "supplier_risk", "executive_report"}


def test_post_hello_world_returns_expected_shape(client):
    resp = client.post("/agents/hello_world", json={"input": {"name": "Pytest"}})
    assert resp.status_code == 200

    body = resp.json()
    assert "greeting" in body
    assert "citations" in body
    for key in (
        "audit_log_id",
        "model",
        "latency_ms",
        "turns_used",
        "tool_call_trace",
        "memory_ids",
        "output_valid",
        "error",
    ):
        assert key in body


def test_post_nonexistent_agent_returns_404(client):
    resp = client.post("/agents/nonexistent", json={"input": {}})
    assert resp.status_code == 404


def test_get_approvals_returns_200_with_paginated_list(client):
    resp = client.get("/approvals")
    assert resp.status_code == 200

    body = resp.json()
    for key in ("items", "total", "limit", "offset"):
        assert key in body
    assert isinstance(body["items"], list)


def test_list_audit_logs_returns_200_with_paginated_list(client):
    resp = client.get("/audit-logs")
    assert resp.status_code == 200

    body = resp.json()
    for key in ("items", "total", "limit", "offset"):
        assert key in body
    assert isinstance(body["items"], list)


def test_list_audit_logs_filters_by_workflow(client, db_session):
    db_session.add(
        AIAuditLog(
            workflow="_test_audit_workflow",
            model="fake-model",
            prompt="test prompt",
            output="{}",
            output_valid=True,
        )
    )
    db_session.flush()

    resp = client.get("/audit-logs", params={"workflow": "_test_audit_workflow"})
    assert resp.status_code == 200

    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["workflow"] == "_test_audit_workflow"


def test_get_audit_log_returns_404_for_missing_id(client):
    resp = client.get("/audit-logs/999999")
    assert resp.status_code == 404
