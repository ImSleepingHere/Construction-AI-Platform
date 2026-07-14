"""Tests for the memory tools (app/agents/memory.py).

get_llm_client() is monkeypatched to a FakeLLMClient wherever a test would
otherwise trigger a real embed() call -- these are meant to run offline.
"""

from __future__ import annotations

from app.agents.tools import execute_tool, registry
from app.models.ai_layer import AIMemory

from tests.conftest import FakeLLMClient


def test_store_memory_valid_input_inserts_and_returns_row(db_session, monkeypatch):
    mock_llm = FakeLLMClient()
    monkeypatch.setattr("app.agents.memory.get_llm_client", lambda: mock_llm)

    td = registry.get("store_memory")
    result = execute_tool(
        td,
        db_session,
        {"category": "insight", "content": "Test memory content.", "confidence": 0.85},
    )

    assert "id" in result
    assert result["category"] == "insight"
    assert result["content"] == "Test memory content."

    row = db_session.get(AIMemory, result["id"])
    assert row is not None
    assert row.content == "Test memory content."
    assert row.embedding is not None  # store_memory computes one via get_llm_client()


def test_store_memory_bad_category_returns_error_dict_not_exception(db_session, monkeypatch):
    mock_llm = FakeLLMClient()
    monkeypatch.setattr("app.agents.memory.get_llm_client", lambda: mock_llm)

    td = registry.get("store_memory")
    result = execute_tool(
        td, db_session, {"category": "not_a_real_category", "content": "Whatever."}
    )

    assert "error" in result
    # Category is invalid before any embed() call happens.
    assert mock_llm.embed_calls == []


def test_search_memory_keyword_match(db_session, monkeypatch):
    mock_llm = FakeLLMClient()
    monkeypatch.setattr("app.agents.memory.get_llm_client", lambda: mock_llm)

    row = AIMemory(
        category="insight",
        content="The unmistakable zephyrsaurus delivery was delayed.",
        source_reference={"type": "test"},
        confidence=0.9,
        extracted_by="test",
    )
    db_session.add(row)
    db_session.flush()

    td = registry.get("search_memory")
    result = execute_tool(
        td, db_session, {"query": "zephyrsaurus", "use_semantic": False}
    )

    assert any(r["id"] == row.id for r in result)


def test_search_memory_semantic_ranks_by_similarity_when_embedding_present(db_session, monkeypatch):
    query_vector = [1.0] + [0.0] * 767
    orthogonal_vector = [0.0, 1.0] + [0.0] * 766

    close = AIMemory(
        category="insight",
        content="Semantically close memory.",
        source_reference={"type": "test"},
        confidence=0.9,
        extracted_by="test",
        embedding=query_vector,
    )
    far = AIMemory(
        category="insight",
        content="Semantically distant memory.",
        source_reference={"type": "test"},
        confidence=0.9,
        extracted_by="test",
        embedding=orthogonal_vector,
    )
    db_session.add_all([close, far])
    db_session.flush()

    mock_llm = FakeLLMClient()
    mock_llm.embed = lambda text, **kw: query_vector  # query embeds identically to `close`
    monkeypatch.setattr("app.agents.memory.get_llm_client", lambda: mock_llm)

    td = registry.get("search_memory")
    result = execute_tool(
        td, db_session, {"query": "irrelevant text, embedding is mocked", "limit": 5}
    )

    # `close` is an exact embedding match (cosine distance 0, the global
    # minimum), so it always ranks first regardless of what else is in the
    # table -- unlike asserting `far`'s relative position, which would be
    # fragile against whatever real memories already exist in the DB.
    ids = [r["id"] for r in result]
    assert ids[0] == close.id
