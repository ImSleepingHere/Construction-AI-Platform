"""Agent registry: discovers BaseAgent subclasses under app/agents/<name>/.

Discovery rule: a subfolder of app/agents/ counts as an agent package if it
contains both SKILL.md and agent.py. Its agent.py is imported and scanned for
a single BaseAgent subclass, which is registered under the skill's `name`
(from SKILL.md frontmatter, not the folder name).

Discovery runs once, lazily, on first access.
"""

from __future__ import annotations

import importlib
import inspect
from pathlib import Path

from app.agents.base import BaseAgent

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
