"""Tool-calling smoke test. Delete after verifying."""

from pydantic import BaseModel, Field

from app.agents.base import AgentContext, BaseAgent


class ToolTestOutput(BaseModel):
    answer: str = Field(description="Short factual answer.")
    citations: list[int] = Field(
        default_factory=list,
        description="Memory ids used to formulate the answer.",
    )


class ToolTestAgent(BaseAgent):
    skill_path = __file__
    output_model = ToolTestOutput

    def prepare_input(self, ctx: AgentContext) -> str:
        return f"Question: {ctx.input['question']}"