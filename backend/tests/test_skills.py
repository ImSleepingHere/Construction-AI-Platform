"""Tests for the SKILL.md loader (app/agents/skills.py).

Pure file-parsing tests against pytest's tmp_path -- no DB, no LLM.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.agents.skills import load_skill


def _write_skill(tmp_path: Path, frontmatter: str, body: str = "Body text here.") -> Path:
    skill_md = tmp_path / "SKILL.md"
    skill_md.write_text(f"---\n{frontmatter}\n---\n\n{body}\n", encoding="utf-8")
    return skill_md


def test_frontmatter_parsing_works(tmp_path):
    skill_md = _write_skill(
        tmp_path,
        "name: test_skill\ndescription: A test skill\noutput_schema: TestOutput",
    )
    skill = load_skill(skill_md)

    assert skill.name == "test_skill"
    assert skill.description == "A test skill"
    assert skill.output_schema == "TestOutput"
    assert skill.max_turns == 1
    assert skill.tools == []
    assert skill.grounding == "lenient"
    assert "Body text here." in skill.system_prompt


def test_missing_required_fields_raises(tmp_path):
    skill_md = _write_skill(tmp_path, "name: test_skill")
    with pytest.raises(ValueError, match="missing required frontmatter fields"):
        load_skill(skill_md)


@pytest.mark.parametrize("grounding_line", ['grounding: "off"', "grounding: off"])
def test_quoted_and_unquoted_off_both_parse_to_off(tmp_path, grounding_line):
    skill_md = _write_skill(
        tmp_path,
        f"name: test_skill\ndescription: d\noutput_schema: O\n{grounding_line}",
    )
    skill = load_skill(skill_md)
    assert skill.grounding == "off"


def test_malformed_yaml_raises_helpful_message(tmp_path):
    skill_md = _write_skill(tmp_path, "name: [unclosed")
    with pytest.raises(ValueError, match="invalid YAML frontmatter"):
        load_skill(skill_md)


def test_missing_file_raises_file_not_found(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_skill(tmp_path / "does_not_exist.md")
