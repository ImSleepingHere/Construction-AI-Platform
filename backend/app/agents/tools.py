"""Tool registry: decorators and metadata for callable functions exposed to LLM agents.

Design choices:
- Tools are regular Python functions with a @tool decorator. No config files.
- Registration happens on import via the decorator's side effect.
- The registry knows two things per tool: its callable and its JSON schema
  (auto-derived from type hints).
- Tools accept a `db: Session` first positional arg, injected by the framework.
  They should not receive `db` from the LLM.
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from typing import Any, Callable, get_type_hints

from sqlalchemy.orm import Session


# --- Registry ---


@dataclass
class ToolDefinition:
    """Everything the framework needs to expose and execute a tool."""

    name: str
    description: str
    func: Callable[..., Any]
    parameters_schema: dict[str, Any]
    # LLM-facing param names (excludes `db` which is framework-injected)
    llm_param_names: list[str] = field(default_factory=list)


class ToolRegistry:
    """Global registry. Tools self-register at import time via @tool."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, tool_def: ToolDefinition) -> None:
        if tool_def.name in self._tools:
            raise ValueError(
                f"Tool {tool_def.name!r} is already registered. "
                "Tool names must be unique."
            )
        self._tools[tool_def.name] = tool_def

    def get(self, name: str) -> ToolDefinition:
        if name not in self._tools:
            raise KeyError(f"Tool {name!r} not found in registry")
        return self._tools[name]

    def has(self, name: str) -> bool:
        return name in self._tools

    def list_names(self) -> list[str]:
        return sorted(self._tools.keys())

    def subset(self, names: list[str]) -> list[ToolDefinition]:
        """Return the tools with the given names, preserving order."""
        return [self.get(name) for name in names]


# Global registry. Tools appear here on import.
registry = ToolRegistry()


# --- Type -> JSON schema mapping ---

_TYPE_MAP = {
    int: "integer",
    str: "string",
    float: "number",
    bool: "boolean",
    list: "array",
    dict: "object",
}


def _python_type_to_json_type(py_type: Any) -> str:
    origin = getattr(py_type, "__origin__", None)
    if origin is not None:
        return _TYPE_MAP.get(origin, "string")
    return _TYPE_MAP.get(py_type, "string")


# --- The decorator ---


def tool(
    *,
    name: str | None = None,
    description: str,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Register a Python function as an LLM-callable tool.

    Usage:
        @tool(name="get_supplier_stats", description="Return delivery stats for a supplier.")
        def get_supplier_stats(db: Session, supplier_id: int) -> dict:
            ...

    The `db: Session` parameter is framework-injected. All other parameters are
    exposed to the LLM. Types are derived from Python type hints.
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        tool_name = name or func.__name__

        sig = inspect.signature(func)
        hints = get_type_hints(func)

        properties: dict[str, Any] = {}
        required: list[str] = []
        llm_param_names: list[str] = []

        for param_name, param in sig.parameters.items():
            # Framework-injected params are not exposed to the LLM
            if param_name == "db":
                continue

            hint = hints.get(param_name, str)
            json_type = _python_type_to_json_type(hint)

            properties[param_name] = {"type": json_type}
            llm_param_names.append(param_name)

            if param.default is inspect.Parameter.empty:
                required.append(param_name)

        parameters_schema = {
            "type": "object",
            "properties": properties,
            "required": required,
        }

        tool_def = ToolDefinition(
            name=tool_name,
            description=description,
            func=func,
            parameters_schema=parameters_schema,
            llm_param_names=llm_param_names,
        )
        registry.register(tool_def)

        return func

    return decorator


# --- Execution helper ---


def execute_tool(
    tool_def: ToolDefinition,
    db: Session,
    arguments: dict[str, Any],
) -> Any:
    """Execute a registered tool with LLM-supplied arguments.

    Filters out any args the LLM sent that the tool doesn't accept. Missing
    required args raise TypeError, which the framework converts into a
    tool-error result the LLM can see and correct.
    """
    filtered = {k: v for k, v in arguments.items() if k in tool_def.llm_param_names}
    return tool_def.func(db, **filtered)