"""Run the tool-calling smoke test. Delete after verifying."""

import json

import app.agents  # noqa: F401 — register memory tools
from app.agents._tool_test.agent import ToolTestAgent
from app.agents.tools import execute_tool, registry
from app.core.database import SessionLocal


if __name__ == "__main__":
    # Seed a memory the agent should be able to find.
    with SessionLocal() as db:
        store = registry.get("store_memory")
        execute_tool(
            store,
            db=db,
            arguments={
                "category": "insight",
                "content": "Supplier BuildRight is known for delivering rebar on time in the Eastern Province.",
                "confidence": 0.9,
            },
        )
        db.commit()

    # Run the agent.
    agent = ToolTestAgent()
    with SessionLocal() as db:
        result = agent.run(db, {"question": "What do we know about supplier BuildRight?"})

    print(f"output_valid: {result.output_valid}")
    print(f"error:        {result.error}")
    print(f"audit_log_id: {result.audit_log_id}")
    print(f"model:        {result.model}")
    print(f"latency_ms:   {result.latency_ms}")
    print(f"turns_used:   {result.turns_used}")
    print()
    print(f"Tool call trace ({len(result.tool_call_trace)} calls):")
    for call in result.tool_call_trace:
        print(f"  Turn {call['turn']}: {call['tool']}({call['arguments']})")
        output_snippet = json.dumps(call['output'])[:100]
        print(f"    -> {output_snippet}")
    print()
    if result.output:
        print(f"answer:    {result.output.answer}")
        print(f"citations: {result.output.citations}")