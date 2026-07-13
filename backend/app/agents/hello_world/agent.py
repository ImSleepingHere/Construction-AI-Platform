from __future__ import annotations

from app.agents.base import AgentContext, BaseAgent
from app.agents.hello_world.schemas import HelloOutput


class HelloWorldAgent(BaseAgent):
    skill_path = __file__
    output_model = HelloOutput

    def prepare_input(self, ctx: AgentContext) -> str:
        name = ctx.input.get("name", "world")
        return f"Name: {name}"
