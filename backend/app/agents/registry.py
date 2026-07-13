"""Agent registry: discovers BaseAgent subclasses under app/agents/<name>/.

Discovery rule: a subfolder of app/agents/ counts as an agent package if it
contains both SKILL.md and agent.py. Its agent.py is imported and scanned for
a single BaseAgent subclass, which is registered under the skill's `name`
(from SKILL.md frontmatter, not the folder name).

After discovery, every agent is also registered as a subagent tool in the
global ToolRegistry, so any agent can declare another agent's skill name in
its own SKILL.md `tools:` list and call it mid-loop. Budget and depth are
threaded through AgentContext -> subagent tool closure -> child run() -> back
into the parent's ctx.call_budget, so the whole call tree shares one budget.

Discovery runs once, lazily, on first access.
"""

from __future__ import annotations

import importlib
import inspect
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.agents.base import AgentContext, BaseAgent
from app.agents.tools import ToolDefinition, registry as tool_registry

_AGENTS_DIR = Path(__file__).parent

_agents: dict[str, BaseAgent] = {}
_scanned = False


def _discover() -> None:
    global _scanned
    if _scanned:
        return
    _scanned = True

    for entry in sorted(_AGENTS_DIR.iterdir()):
        if not entry.is_dir() or entry.name == "__pycache__":
            continue
        skill_md = entry / "SKILL.md"
        agent_py = entry / "agent.py"
        if not (skill_md.exists() and agent_py.exists()):
            continue

        module_name = f"app.agents.{entry.name}.agent"
        module = importlib.import_module(module_name)

        agent_cls: type[BaseAgent] | None = None
        for _, obj in inspect.getmembers(module, inspect.isclass):
            if (
                issubclass(obj, BaseAgent)
                and obj is not BaseAgent
                and obj.__module__ == module_name
            ):
                agent_cls = obj
                break

        if agent_cls is None:
            raise ValueError(f"{module_name}: no BaseAgent subclass found")

        instance = agent_cls()
        skill_name = instance.skill.name
        if skill_name in _agents:
            raise ValueError(
                f"Duplicate skill name {skill_name!r}: already registered, "
                f"collision from {entry.name}"
            )
        _agents[skill_name] = instance

    _register_subagent_tools()


def _make_subagent_tool(skill_name: str, agent: BaseAgent) -> ToolDefinition:
    def _call_subagent(db: Session, ctx: AgentContext, input: dict[str, Any]) -> dict[str, Any]:
        new_depth = ctx.depth + 1
        if new_depth > ctx.max_depth:
            return {"error": "Max subagent depth exceeded"}

        result = agent.run(
            db,
            input,
            call_budget=ctx.call_budget,
            depth=new_depth,
            max_depth=ctx.max_depth,
        )
        # Propagate whatever the subagent spent back into the parent's budget.
        ctx.call_budget = result.call_budget_remaining

        if not result.output_valid:
            return {
                "error": result.error or "Subagent run failed",
                "audit_log_id": result.audit_log_id,
            }
        return result.output.model_dump()

    return ToolDefinition(
        name=skill_name,
        description=agent.skill.description,
        func=_call_subagent,
        parameters_schema={
            "type": "OBJECT",
            "properties": {"input": {"type": "OBJECT"}},
            "required": ["input"],
        },
        llm_param_names=["input"],
        context_param="ctx",
    )


def _register_subagent_tools() -> None:
    for skill_name, agent in _agents.items():
        if tool_registry.has(skill_name):
            continue  # a plain @tool already claims this name; don't shadow it
        tool_registry.register(_make_subagent_tool(skill_name, agent))


def get_agent(skill_name: str) -> BaseAgent:
    _discover()
    if skill_name not in _agents:
        raise KeyError(
            f"No agent registered for skill {skill_name!r}. "
            f"Known: {sorted(_agents)}"
        )
    return _agents[skill_name]


def list_agents() -> list[dict[str, str]]:
    _discover()
    return [
        {
            "name": agent.skill.name,
            "description": agent.skill.description,
            "version": agent.skill.version,
        }
        for _, agent in sorted(_agents.items())
    ]
