from __future__ import annotations

from pydantic import BaseModel, Field


class HelloOutput(BaseModel):
    greeting: str = Field(description="Friendly greeting that includes the given name.")
    citations: list[int] = Field(
        default_factory=list,
        description="Memory ids referenced while producing the greeting, if any. Empty if none.",
    )
