from __future__ import annotations

from pydantic import BaseModel, Field


class ReportSection(BaseModel):
    title: str
    key_points: list[str] = Field(
        default_factory=list, description="2-5 bullet points for this section."
    )
    supporting_data: list[str] = Field(
        default_factory=list,
        description=(
            "Numbers/counts referenced in this section as short 'label: value' "
            "strings, e.g. 'overdue_pos: 4', 'avg_delay_days: 12.5'. This SDK's "
            "structured-output schema can't express a free-form dict (an OBJECT "
            "with no declared properties always comes back empty), so a list "
            "of label:value strings is used instead."
        ),
    )


class WeeklyReport(BaseModel):
    week_of: str = Field(description="ISO date (YYYY-MM-DD) this report covers.")
    executive_summary: str = Field(description="3-5 sentences for leadership.")
    sections: list[ReportSection] = Field(default_factory=list)
    top_recommendations: list[str] = Field(
        default_factory=list, description="3-5 action items."
    )
    confidence: float = Field(ge=0.0, le=1.0)
