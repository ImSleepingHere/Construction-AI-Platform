"""SKILL.md loader.

Every agent's folder contains a SKILL.md file:
- YAML frontmatter (--- delimited) with declarative metadata
- Markdown body used as the LLM's system prompt

Design choices:
- The SKILL.md is the source of truth for the prompt. Change it, restart, done.
- Frontmatter fields are validated into a typed dataclass so agents get
  autocomplete on `skill.name` etc., not dict lookups.
- Loading is done once at agent init (in BaseAgent.__init__), not per request.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


# Grounding modes controlling behavior when memory retrieval returns nothing.
VALID_GROUNDING_MODES = {"strict", "lenient", "off"}


@dataclass
class Skill:
    """Parsed contents of a SKILL.md file.

    Frontmatter fields:
        name:           canonical skill identifier (matches folder name)
        description:    one-line description used in tool listings if this
                        skill is exposed as a subagent-tool
        version:        semver-ish string, for tracking prompt evolution
        max_turns:      hard cap on tool-calling loop iterations (1 = workflow)
        tools:          list of tool names this skill may invoke
        output_schema:  Pydantic class name for the final structured output
        grounding:      "strict" | "lenient" | "off"

    Body:
        system_prompt:  everything after the frontmatter, used as-is
    """

    name: str
    description: str
    version: str
    max_turns: int
    tools: list[str]
    output_schema: str
    grounding: str
    system_prompt: str
    raw_frontmatter: dict[str, Any] = field(default_factory=dict)


_FRONTMATTER_RE = re.compile(
    r"\A---\s*\n(?P<meta>.*?)\n---\s*\n(?P<body>.*)\Z",
    re.DOTALL,
)


def load_skill(path: str | Path) -> Skill:
    """Read a SKILL.md file and return a parsed Skill.

    Raises ValueError if the file is missing required fields or malformed.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"SKILL.md not found at {path}")

    text = path.read_text(encoding="utf-8")

    match = _FRONTMATTER_RE.match(text)
    if not match:
        raise ValueError(
            f"{path}: no YAML frontmatter found. "
            "SKILL.md must start with '---' and close with '---'."
        )

    try:
        meta = yaml.safe_load(match.group("meta")) or {}
    except yaml.YAMLError as exc:
        raise ValueError(f"{path}: invalid YAML frontmatter: {exc}") from exc

    if not isinstance(meta, dict):
        raise ValueError(f"{path}: frontmatter must be a YAML mapping, got {type(meta)}")

    # Required fields
    required = ["name", "description", "output_schema"]
    missing = [k for k in required if k not in meta]
    if missing:
        raise ValueError(f"{path}: missing required frontmatter fields: {missing}")

    grounding = meta.get("grounding", "lenient")
    if grounding not in VALID_GROUNDING_MODES:
        raise ValueError(
            f"{path}: grounding must be one of {VALID_GROUNDING_MODES}, got {grounding!r}"
        )

    max_turns = int(meta.get("max_turns", 1))
    if max_turns < 1:
        raise ValueError(f"{path}: max_turns must be >= 1, got {max_turns}")

    tools = meta.get("tools", []) or []
    if not isinstance(tools, list):
        raise ValueError(f"{path}: 'tools' must be a list, got {type(tools)}")

    system_prompt = match.group("body").strip()
    if not system_prompt:
        raise ValueError(f"{path}: system prompt (markdown body) is empty")

    return Skill(
        name=str(meta["name"]),
        description=str(meta["description"]),
        version=str(meta.get("version", "0.1")),
        max_turns=max_turns,
        tools=[str(t) for t in tools],
        output_schema=str(meta["output_schema"]),
        grounding=grounding,
        system_prompt=system_prompt,
        raw_frontmatter=meta,
    )