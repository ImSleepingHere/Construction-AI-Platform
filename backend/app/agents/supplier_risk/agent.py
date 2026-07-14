from __future__ import annotations

from app.agents.base import AgentContext, BaseAgent
from app.agents.supplier_risk.schemas import SupplierRiskAssessment


class SupplierRiskAgent(BaseAgent):
    skill_path = __file__
    output_model = SupplierRiskAssessment

    def prepare_input(self, ctx: AgentContext) -> str:
        supplier_id = ctx.input["supplier_id"]
        horizon_months = ctx.input.get("horizon_months", 6)
        return (
            f"Assess risk for supplier_id={supplier_id}. Consider roughly the "
            f"last {horizon_months} months of activity where the data lets you "
            "distinguish recency; otherwise use the full history available."
        )

    def on_success(self, ctx: AgentContext, output: SupplierRiskAssessment) -> None:
        ctx.store_memory(
            category="risk_assessment",
            content=(
                f"Supplier {output.supplier_name} (id={output.supplier_id}): "
                f"risk_score={output.risk_score} ({output.overall_severity}). "
                f"{output.summary}"
            ),
            confidence=output.confidence,
        )
