from __future__ import annotations

from datetime import date

from app.agents.base import AgentContext, BaseAgent
from app.agents.executive_report.schemas import WeeklyReport


class ExecutiveReportAgent(BaseAgent):
    skill_path = __file__
    output_model = WeeklyReport

    def prepare_input(self, ctx: AgentContext) -> str:
        week_of = ctx.input.get("week_of") or date.today().isoformat()
        return (
            f"Prepare the weekly management report for the week of {week_of}. "
            "Synthesize across the whole active project portfolio."
        )

    def on_success(self, ctx: AgentContext, output: WeeklyReport) -> None:
        section_titles = ", ".join(s.title for s in output.sections) or "no sections"
        ctx.store_memory(
            category="insight",
            content=(
                f"Weekly report for {output.week_of}: {output.executive_summary} "
                f"Sections covered: {section_titles}."
            ),
            confidence=output.confidence,
        )
