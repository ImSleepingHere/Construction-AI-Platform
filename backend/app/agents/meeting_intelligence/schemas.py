"""Pydantic schemas for the Meeting Intelligence agent.

The output schema is authoritative — it's what the LLM must match and what
the framework validates the parsed response against.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class ActionItem(BaseModel):
    """A concrete follow-up assigned to someone."""

    description: str = Field(description="What needs to be done, one sentence.")
    owner: str = Field(description="Person or role responsible.")
    due_date: Optional[str] = Field(
        default=None,
        description="ISO date if a deadline is mentioned; null otherwise.",
    )
    priority: Literal["low", "medium", "high"] = Field(
        default="medium", description="Best-effort inferred priority."
    )


class Decision(BaseModel):
    """A decision that was made during the meeting."""

    description: str = Field(description="What was decided, one sentence.")
    rationale: Optional[str] = Field(
        default=None, description="Reason given, if any."
    )
    owner: Optional[str] = Field(
        default=None, description="Person accountable for the decision."
    )


class Risk(BaseModel):
    """A risk or blocker surfaced in the meeting."""

    description: str = Field(description="The risk, one sentence.")
    severity: Literal["low", "medium", "high"] = Field(
        default="medium", description="Best-effort severity."
    )


class MeetingAnalysis(BaseModel):
    """The LLM's structured output. This shape is enforced strictly.

    If the model can't fill a section (e.g. no risks discussed), it must return
    an empty list, not omit the field.
    """

    summary: str = Field(
        description="2-4 sentence executive summary of the meeting.",
        min_length=20,
        max_length=1200,
    )
    action_items: list[ActionItem] = Field(default_factory=list)
    decisions: list[Decision] = Field(default_factory=list)
    risks: list[Risk] = Field(default_factory=list)
    confidence: float = Field(
        ge=0.0, le=1.0,
        description=(
            "Self-reported confidence in the analysis, 0-1. Should reflect "
            "how clear the input was and how much had to be inferred."
        ),
    )
