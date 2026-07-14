"""Tests for BaseAgent's run pipeline (app/agents/base.py).

Uses real, already-built agents (meeting_intelligence for single-turn,
hello_world for tool-calling) with a FakeLLMClient swapped in, so these
exercise the real SKILL.md/schema wiring without ever hitting Gemini.
"""

from __future__ import annotations

import json

from app.agents.base import AgentContext
from app.agents.meeting_intelligence.agent import MeetingIntelligenceAgent
from app.agents.hello_world.agent import HelloWorldAgent
from app.agents.registry import _make_subagent_tool, get_agent
from app.agents.tools import execute_tool
from app.models.ai_layer import AIAuditLog
from app.services.llm_client import LLMResult, ToolCall

from tests.conftest import FakeLLMClient


VALID_MEETING_JSON = json.dumps(
    {
        "summary": "Team discussed the rebar delivery delay and agreed a mitigation plan.",
        "action_items": [],
        "decisions": [],
        "risks": [],
        "confidence": 0.8,
    }
)


def test_single_turn_agent_completes_with_valid_json(db_session):
    mock_llm = FakeLLMClient(responses=[LLMResult(text=VALID_MEETING_JSON, model="fake-model")])
    agent = MeetingIntelligenceAgent(llm=mock_llm)

    result = agent.run(db_session, {"notes": "Team discussed the rebar delivery delay."})

    assert result.output_valid is True
    assert result.output.summary.startswith("Team discussed")
    assert result.error is None
    assert len(mock_llm.generate_calls) == 1


def test_invalid_json_marks_output_invalid_but_still_writes_audit_log(db_session):
    mock_llm = FakeLLMClient(responses=[LLMResult(text="not valid json{", model="fake-model")])
    agent = MeetingIntelligenceAgent(llm=mock_llm)

    result = agent.run(db_session, {"notes": "Team discussed the rebar delivery delay."})

    assert result.output_valid is False
    assert result.output is None
    assert result.error is not None

    audit_row = db_session.get(AIAuditLog, result.audit_log_id)
    assert audit_row is not None
    assert audit_row.output_valid is False
    assert audit_row.error == result.error


def test_tool_calling_agent_executes_tools_in_order_and_grows_conversation(db_session, monkeypatch):
    # hello_world's SKILL.md has max_turns: 3. Turn 3 is the schema-forced
    # final turn (use_tools=False there), so giving turns 1-2 tool calls and
    # turn 3 a valid final JSON exercises the full loop deterministically.
    responses = [
        LLMResult(
            text="",
            model="fake-model",
            tool_calls=[ToolCall(name="search_memory", arguments={"query": "Ada"})],
        ),
        LLMResult(
            text="",
            model="fake-model",
            tool_calls=[
                ToolCall(
                    name="store_memory",
                    arguments={"category": "hello_greeting", "content": "Greeted Ada."},
                )
            ],
        ),
        LLMResult(
            text=json.dumps({"greeting": "Hello Ada!", "citations": []}),
            model="fake-model",
        ),
    ]
    mock_llm = FakeLLMClient(responses=responses)
    # search_memory/store_memory call get_llm_client() directly (not
    # agent.llm) for embeddings -- patch that too so nothing hits Gemini.
    monkeypatch.setattr("app.agents.memory.get_llm_client", lambda: mock_llm)
    agent = HelloWorldAgent(llm=mock_llm)

    result = agent.run(db_session, {"name": "Ada"})

    assert result.output_valid is True
    assert result.output.greeting == "Hello Ada!"
    assert result.turns_used == 3
    assert [c["tool"] for c in result.tool_call_trace] == ["search_memory", "store_memory"]
    assert [c["turn"] for c in result.tool_call_trace] == [1, 2]

    # Conversation grows across calls: call 2 sees more history than call 1.
    assert len(mock_llm.generate_calls) == 3
    len_after_call_1 = len(mock_llm.generate_calls[1]["conversation"])
    len_after_call_2 = len(mock_llm.generate_calls[2]["conversation"])
    assert len_after_call_2 > len_after_call_1


def test_budget_exhaustion_returns_error_without_raising(db_session):
    mock_llm = FakeLLMClient(responses=[LLMResult(text=VALID_MEETING_JSON, model="fake-model")])
    agent = MeetingIntelligenceAgent(llm=mock_llm)

    result = agent.run(
        db_session, {"notes": "Team discussed the rebar delivery delay."}, call_budget=0
    )

    assert result.output_valid is False
    assert result.error == "Agent budget exhausted"
    # The budget check happens before any LLM call.
    assert mock_llm.generate_calls == []


def test_max_depth_exceeded_prevents_subagent_invocation(db_session):
    hello_world_agent = get_agent("hello_world")
    subagent_tool = _make_subagent_tool("hello_world", hello_world_agent)

    ctx = AgentContext(db=db_session, input={}, depth=2, max_depth=2)
    result = execute_tool(
        subagent_tool, db_session, {"input": {"name": "Ada"}}, context=ctx
    )

    assert result == {"error": "Max subagent depth exceeded"}
