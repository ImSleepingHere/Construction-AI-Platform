"""Intent classification for the /chat routing endpoint.

Given a free-text message, decides which of the 3 domain agents (if any)
should handle it, and extracts just enough structured input to invoke that
agent -- in one LLM call, so /chat never needs a second round trip to figure
out what to pass the chosen agent.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.services.llm_client import LLMClient, LLMResult

DOMAIN_AGENTS = ["meeting_intelligence", "supplier_risk", "executive_report"]

SYSTEM_INSTRUCTION_TEMPLATE = """You route user messages to the right specialized agent \
for a construction project management platform, or answer directly if none apply.

AGENTS:
- meeting_intelligence: {meeting_intelligence_desc}
- supplier_risk: {supplier_risk_desc}
- executive_report: {executive_report_desc}

RULES:
1. Pick the single best-fitting agent, or "none" if the message is a general \
question, greeting, or anything none of the three agents are built to answer.
2. If agent is meeting_intelligence, copy the meeting notes/content from the \
message into meeting_notes verbatim. If there's no actual meeting content to \
analyze, choose "none" instead.
3. If agent is supplier_risk, extract the supplier id as an integer into \
supplier_id. If no numeric id is present in the message, choose "none" instead \
-- do not guess an id.
4. If agent is "none", write a short, direct, helpful answer in plain_response.
5. Reply with a single JSON object matching the schema. No prose outside the JSON.
6. Never backslash-escape an apostrophe in JSON string values (write "I've", \
not "I\\'ve") -- that is not a valid JSON escape.
"""


class IntentClassification(BaseModel):
    agent: Literal["meeting_intelligence", "supplier_risk", "executive_report", "none"] = (
        Field(description="Which agent should handle this message, or 'none'.")
    )
    supplier_id: int = Field(
        default=0, description="Supplier id if agent is supplier_risk, else 0."
    )
    meeting_notes: str = Field(
        default="",
        description="Meeting content if agent is meeting_intelligence, else empty.",
    )
    plain_response: str = Field(
        default="", description="Direct answer if agent is 'none', else empty."
    )


def classify_intent(
    llm: LLMClient, message: str, agent_descriptions: dict[str, str]
) -> tuple[IntentClassification, LLMResult]:
    """Classify a message and return (classification, raw LLMResult).

    The raw LLMResult is returned too so the caller can log token usage /
    latency without a second call.
    """
    system_instruction = SYSTEM_INSTRUCTION_TEMPLATE.format(
        meeting_intelligence_desc=agent_descriptions.get("meeting_intelligence", ""),
        supplier_risk_desc=agent_descriptions.get("supplier_risk", ""),
        executive_report_desc=agent_descriptions.get("executive_report", ""),
    )
    result = llm.generate(
        prompt=f"User message: {message}",
        system_instruction=system_instruction,
        response_schema=IntentClassification,
        temperature=0.1,
    )
    classification = IntentClassification.model_validate_json(result.text)
    return classification, result
