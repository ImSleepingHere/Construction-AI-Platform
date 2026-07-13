"""BaseAgent framework class.

Handles the run pipeline: prompt build -> LLM call(s) -> validation ->
success hook -> audit persistence -> memory persistence.

Supports two modes:
- Single-turn workflow: skill has no tools, one LLM call, structured output.
- Tool-calling loop: skill declares tools, up to max_turns iterations of
  (LLM emits tool call -> we execute -> feed result back), then final
  structured output.
"""

from __future__ import annotations

import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, ClassVar, Optional

import app.models  # noqa: F401 - ensures all model tables are registered

from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session

from app.agents.skills import Skill, load_skill
from app.agents.tools import execute_tool, registry as tool_registry
from app.models.ai_layer import AIAuditLog, AIMemory
from app.services.llm_client import LLMClient, LLMResult, ToolCall, get_llm_client


# --- Context object ---


@dataclass
class AgentContext:
    db: Session
    input: dict[str, Any]
    project_id: Optional[int] = None
    prompt: str = ""
    llm_output_raw: Optional[str] = None
    llm_model: Optional[str] = None
    llm_latency_ms: int = 0
    llm_prompt_tokens: Optional[int] = None
    llm_completion_tokens: Optional[int] = None
    retrieved_source_ids: list[dict[str, Any]] = field(default_factory=list)
    _pending_memories: list[dict[str, Any]] = field(default_factory=list)
    audit_log_id: Optional[int] = None
    # Populated in tool-calling runs.
    tool_call_trace: list[dict[str, Any]] = field(default_factory=list)
    turns_used: int = 0

    def store_memory(
        self,
        *,
        category: str,
        content: str,
        confidence: float = 0.7,
        source_reference: Optional[dict[str, Any]] = None,
    ) -> None:
        self._pending_memories.append({
            "category": category,
            "content": content,
            "confidence": confidence,
            "source_reference": source_reference,
        })


@dataclass
class AgentResult:
    output: Optional[BaseModel]
    output_valid: bool
    error: Optional[str]
    audit_log_id: int
    memory_ids: list[int]
    model: str
    latency_ms: int
    project_id: Optional[int]
    tool_call_trace: list[dict[str, Any]] = field(default_factory=list)
    turns_used: int = 0


class BaseAgent(ABC):
    skill_path: ClassVar[str]
    output_model: ClassVar[type[BaseModel]]

    def __init__(self, llm: Optional[LLMClient] = None) -> None:
        self.skill: Skill = load_skill(_skill_md_path_from(self.skill_path))
        self.llm: LLMClient = llm or get_llm_client()

    @abstractmethod
    def prepare_input(self, ctx: AgentContext) -> str: ...

    def on_success(self, ctx: AgentContext, output: BaseModel) -> None:
        return None

    # --- Framework-owned run ---

    def run(self, db: Session, input_payload: dict[str, Any]) -> AgentResult:
        ctx = AgentContext(db=db, input=input_payload)

        try:
            ctx.prompt = self.prepare_input(ctx)
        except Exception as exc:
            return self._write_audit_and_return(
                ctx, output=None, error=f"prepare_input failed: {exc}", raise_after=False
            )

        if self.skill.grounding == "strict" and not ctx.retrieved_source_ids:
            return self._write_audit_and_return(
                ctx,
                output=None,
                error="Grounding=strict but no sources retrieved. Refusing LLM call.",
                raise_after=False,
            )

        # Route to tool-calling loop if skill declares tools, else single-turn.
        if self.skill.tools:
            return self._run_with_tools(ctx)
        return self._run_single_turn(ctx)

    # --- Single-turn mode ---

    def _run_single_turn(self, ctx: AgentContext) -> AgentResult:
        call_start = time.perf_counter()
        try:
            result = self.llm.generate(
                prompt=ctx.prompt,
                system_instruction=self.skill.system_prompt,
                response_schema=self.output_model,
                temperature=0.2,
            )
        except Exception as exc:
            ctx.llm_latency_ms = int((time.perf_counter() - call_start) * 1000)
            return self._write_audit_and_return(
                ctx, output=None, error=f"LLM call failed: {exc}", raise_after=False
            )

        self._absorb_llm_result(ctx, result, call_start)
        return self._finalize(ctx, result.text)

    # --- Tool-calling loop mode ---

    def _run_with_tools(self, ctx: AgentContext) -> AgentResult:
        tool_defs = self._build_tool_definitions()
        conversation: list[dict[str, Any]] = [
            {"role": "user", "parts": [{"text": ctx.prompt}]},
        ]

        aggregate_latency_ms = 0
        aggregate_prompt_tokens = 0
        aggregate_completion_tokens = 0

        for turn in range(1, self.skill.max_turns + 1):
            ctx.turns_used = turn
            call_start = time.perf_counter()
            try:
                # Intermediate turns: tools enabled, no schema.
                # Final turn (last iteration): fall back to schema-only.
                use_tools = turn < self.skill.max_turns
                result = self.llm.generate(
                    prompt="",  # conversation carries everything
                    system_instruction=self.skill.system_prompt,
                    response_schema=None if use_tools else self.output_model,
                    tools=tool_defs if use_tools else None,
                    conversation=conversation,
                    temperature=0.2,
                )
            except Exception as exc:
                ctx.llm_latency_ms = int((time.perf_counter() - call_start) * 1000)
                return self._write_audit_and_return(
                    ctx,
                    output=None,
                    error=f"LLM call failed on turn {turn}: {exc}",
                    raise_after=False,
                )

            aggregate_latency_ms += result.latency_ms
            if result.prompt_tokens:
                aggregate_prompt_tokens += result.prompt_tokens
            if result.completion_tokens:
                aggregate_completion_tokens += result.completion_tokens

            # No tool calls => LLM produced its final response.
            if not result.tool_calls:
                ctx.llm_latency_ms = aggregate_latency_ms
                ctx.llm_prompt_tokens = aggregate_prompt_tokens or None
                ctx.llm_completion_tokens = aggregate_completion_tokens or None
                ctx.llm_model = result.model
                ctx.llm_output_raw = result.text
                return self._finalize(ctx, result.text)

            # Execute each tool call and append results to conversation.
            self._execute_tool_calls(ctx, result, conversation)

        # Reached max_turns without a final answer.
        ctx.llm_latency_ms = aggregate_latency_ms
        ctx.llm_prompt_tokens = aggregate_prompt_tokens or None
        ctx.llm_completion_tokens = aggregate_completion_tokens or None
        ctx.llm_model = self.llm._default_model  # best-effort
        return self._write_audit_and_return(
            ctx,
            output=None,
            error=f"Agent hit max_turns ({self.skill.max_turns}) without producing a final answer.",
            raise_after=False,
        )

    # --- Helpers ---

    def _build_tool_definitions(self) -> list[dict[str, Any]]:
        defs = []
        for name in self.skill.tools:
            if not tool_registry.has(name):
                raise ValueError(
                    f"Skill {self.skill.name!r} declared tool {name!r} but it is "
                    f"not registered. Registered tools: {tool_registry.list_names()}"
                )
            td = tool_registry.get(name)
            defs.append({
                "name": td.name,
                "description": td.description,
                "parameters": td.parameters_schema,
            })
        return defs

    def _execute_tool_calls(
            self,
            ctx: AgentContext,
            result: LLMResult,
            conversation: list[Any],
        ) -> None:
            from google.genai import types as genai_types

            # Echo the model's response verbatim, so thought_signatures and any
            # other SDK-managed metadata on the function_call parts survive.
            if result.response_content is not None:
                conversation.append(result.response_content)
            else:
                # Fallback for providers that don't expose raw Content.
                conversation.append({
                    "role": "model",
                    "parts": [
                        {"function_call": {"name": tc.name, "args": tc.arguments}}
                        for tc in result.tool_calls
                    ],
                })

            # Execute each tool and build the function_response turn.
            response_parts = []
            for tc in result.tool_calls:
                try:
                    if not tool_registry.has(tc.name):
                        tool_output: Any = {"error": f"unknown tool {tc.name!r}"}
                    else:
                        td = tool_registry.get(tc.name)
                        tool_output = execute_tool(td, ctx.db, tc.arguments)
                    error_str = None
                except Exception as exc:
                    tool_output = {"error": f"{type(exc).__name__}: {exc}"}
                    error_str = str(exc)

                ctx.tool_call_trace.append({
                    "turn": ctx.turns_used,
                    "tool": tc.name,
                    "arguments": tc.arguments,
                    "output": tool_output,
                    "error": error_str,
                })
                response_parts.append(
                    genai_types.Part.from_function_response(
                        name=tc.name,
                        response={"result": tool_output},
                    )
                )

            conversation.append(
                genai_types.Content(role="user", parts=response_parts)
            )
    def _absorb_llm_result(
        self, ctx: AgentContext, result: LLMResult, call_start: float
    ) -> None:
        ctx.llm_output_raw = result.text
        ctx.llm_model = result.model
        ctx.llm_prompt_tokens = result.prompt_tokens
        ctx.llm_completion_tokens = result.completion_tokens
        ctx.llm_latency_ms = int((time.perf_counter() - call_start) * 1000)

    def _finalize(self, ctx: AgentContext, output_text: str) -> AgentResult:
        parsed_output: Optional[BaseModel] = None
        validation_error: Optional[str] = None
        try:
            parsed_json = json.loads(output_text)
            parsed_output = self.output_model.model_validate(parsed_json)
        except (json.JSONDecodeError, ValidationError) as exc:
            validation_error = f"{type(exc).__name__}: {exc}"

        audit_row = self._write_audit_log(
            ctx,
            output_text=output_text,
            output_valid=parsed_output is not None,
            error=validation_error,
        )
        ctx.audit_log_id = audit_row.id

        if parsed_output is None:
            ctx.db.commit()
            return AgentResult(
                output=None,
                output_valid=False,
                error=validation_error,
                audit_log_id=audit_row.id,
                memory_ids=[],
                model=ctx.llm_model or "",
                latency_ms=ctx.llm_latency_ms,
                project_id=ctx.project_id,
                tool_call_trace=ctx.tool_call_trace,
                turns_used=ctx.turns_used,
            )

        try:
            self.on_success(ctx, parsed_output)
        except Exception as exc:
            audit_row.error = f"on_success raised: {exc}"
            ctx.db.flush()

        memory_ids = self._persist_memories(ctx)
        ctx.db.commit()

        return AgentResult(
            output=parsed_output,
            output_valid=True,
            error=audit_row.error,
            audit_log_id=audit_row.id,
            memory_ids=memory_ids,
            model=ctx.llm_model or "",
            latency_ms=ctx.llm_latency_ms,
            project_id=ctx.project_id,
            tool_call_trace=ctx.tool_call_trace,
            turns_used=ctx.turns_used,
        )

    def _write_audit_log(
        self,
        ctx: AgentContext,
        output_text: Optional[str],
        output_valid: bool,
        error: Optional[str],
    ) -> AIAuditLog:
        row = AIAuditLog(
            workflow=self.skill.name,
            project_id=ctx.project_id,
            model=ctx.llm_model or "unknown",
            prompt=ctx.prompt,
            system_instruction=self.skill.system_prompt,
            output=output_text,
            output_valid=output_valid,
            error=error,
            prompt_tokens=ctx.llm_prompt_tokens,
            completion_tokens=ctx.llm_completion_tokens,
            latency_ms=ctx.llm_latency_ms,
            retrieved_source_ids=ctx.retrieved_source_ids,
            metadata_json={
                "skill_version": self.skill.version,
                "turns_used": ctx.turns_used,
                "tool_call_trace": ctx.tool_call_trace,
            },
        )
        ctx.db.add(row)
        ctx.db.flush()
        return row

    def _persist_memories(self, ctx: AgentContext) -> list[int]:
        memory_ids: list[int] = []
        default_source = {
            "type": "agent_run",
            "workflow": self.skill.name,
            "audit_log_id": ctx.audit_log_id,
        }
        for pending in ctx._pending_memories:
            row = AIMemory(
                project_id=ctx.project_id,
                category=pending["category"],
                content=pending["content"],
                source_reference=pending["source_reference"] or default_source,
                confidence=pending["confidence"],
                extracted_by=self.skill.name,
            )
            ctx.db.add(row)
            ctx.db.flush()
            memory_ids.append(row.id)
        return memory_ids

    def _write_audit_and_return(
        self,
        ctx: AgentContext,
        output: Optional[BaseModel],
        error: str,
        raise_after: bool,
    ) -> AgentResult:
        audit_row = self._write_audit_log(
            ctx, output_text=None, output_valid=False, error=error
        )
        ctx.db.commit()
        if raise_after:
            raise RuntimeError(error)
        return AgentResult(
            output=output,
            output_valid=False,
            error=error,
            audit_log_id=audit_row.id,
            memory_ids=[],
            model=ctx.llm_model or "",
            latency_ms=ctx.llm_latency_ms,
            project_id=ctx.project_id,
            tool_call_trace=ctx.tool_call_trace,
            turns_used=ctx.turns_used,
        )


def _skill_md_path_from(agent_file: str) -> Path:
    return Path(agent_file).parent / "SKILL.md"