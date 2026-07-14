"""Tests for the @tool decorator and ToolRegistry (app/agents/tools.py).

Pure logic tests -- no DB, no LLM. Test tool names are prefixed `_test_` to
avoid colliding with real tool names registered elsewhere in the app.
"""

from __future__ import annotations

from typing import Optional

import pytest

from app.agents.tools import execute_tool, registry, tool


def test_tool_decorator_generates_uppercase_schema():
    @tool(name="_test_schema_tool", description="test")
    def _test_schema_tool(
        db,
        name: str,
        count: int = 3,
        ratio: float = 1.0,
        active: bool = True,
        tags: list = None,
    ):
        return {}

    td = registry.get("_test_schema_tool")
    props = td.parameters_schema["properties"]

    assert props["name"]["type"] == "STRING"
    assert props["count"]["type"] == "INTEGER"
    assert props["ratio"]["type"] == "NUMBER"
    assert props["active"]["type"] == "BOOLEAN"
    assert props["tags"]["type"] == "ARRAY"
    # db is framework-injected, never exposed to the LLM.
    assert "db" not in props
    # Only params without a default are required.
    assert td.parameters_schema["required"] == ["name"]


def test_registry_rejects_duplicate_registration():
    @tool(name="_test_dup_tool", description="test")
    def _test_dup_tool(db):
        return {}

    with pytest.raises(ValueError):

        @tool(name="_test_dup_tool", description="test again")
        def _test_dup_tool_2(db):
            return {}


def test_execute_tool_filters_unknown_args():
    @tool(name="_test_filter_tool", description="test")
    def _test_filter_tool(db, known: str = "default"):
        return {"known": known}

    td = registry.get("_test_filter_tool")
    result = execute_tool(
        td, db=None, arguments={"known": "value", "unknown_arg": "ignored"}
    )
    assert result == {"known": "value"}


def test_optional_type_unwraps_correctly():
    @tool(name="_test_optional_tool", description="test")
    def _test_optional_tool(db, maybe: Optional[str] = None):
        return {}

    td = registry.get("_test_optional_tool")
    assert td.parameters_schema["properties"]["maybe"]["type"] == "STRING"
    assert "maybe" not in td.parameters_schema["required"]
