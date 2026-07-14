from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class RiskFactor(BaseModel):
    description: str = Field(description="The risk factor, one sentence.")
    severity: Literal["low", "medium", "high"]
    evidence: str = Field(
        description=(
            "Cites the specific tool call and data point this factor is "
            "based on, e.g. 'get_supplier_delivery_stats: 8/12 POs late, "
            "avg delay 14.5 days'."
        )
    )


class SupplierRiskAssessment(BaseModel):
    supplier_id: int
    supplier_name: str
    risk_score: int = Field(ge=0, le=100)
    overall_severity: Literal["low", "medium", "high"]
    top_concerns: list[RiskFactor] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    summary: str = Field(description="2-4 sentence summary of the assessment.")
