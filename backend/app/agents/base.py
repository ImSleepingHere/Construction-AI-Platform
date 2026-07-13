"""BaseAgent framework class.

Design:
- Agents inherit from BaseAgent and override two hooks: prepare_input and on_success.
- Everything else — LLM call, retries, validation, audit logging, memory
  extraction — lives in the framework's run() method.
- Every run writes exactly one audit log row, always, whether successful or
  failed. This is the core auditability guarantee.

Single-turn variant only. Multi-turn tool-calling is added in 3.5.5.
"""

from __future__ import annotations

import json
import time
import app.models  # noqa: F401 - ensures all model tables are registered
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, ClassVar, Optional

from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session

from app.agents.skills import Skill, load_skill
from app.models.ai_layer import AIAuditLog, AIMemory
from app.services.llm_client import LLMClient, get_llm_client


# --- Context object ---


@dataclass
class AgentContext:
    """Request-scoped state passed through the agent's lifecycle.

    Agents receive this in prepare_input and on_success. Everything a workflow
    might touch — DB session, input payload, project scope, memory to persist
    — lives here.
    """

    db: Session
    input: dict[str, Any]
    project_id: Optional[int] = None
    # Populated by the framework as the run progresses.
    prompt: str = ""
    llm_output_raw: Optional[str] = None
    llm_model: Optional[str] = None
    llm_latency_ms: int = 0
    llm_prompt_tokens: Optional[int] = None
    llm_completion_tokens: Optional[int] = None
    retrieved_source_ids: list[dict[str, Any]] = field(default_factory=list)
    # Agents use these to accumulate memories to persist on success.
    _pending_memories: list[dict[str, Any]] = field(default_factory=list)
    # Populated by the framework after audit log is written.
    audit_log_id: Optional[int] = None

    def store_memory(
        self,
        *,
        category: str,
        content: str,
        confidence: float = 0.7,
        source_reference: Optional[dict[str, Any]] = None,
    ) -> None:
        """Queue a memory for persistence. Actual write happens after the
        audit log row is written, so memories can reference audit_log_id."""
        self._pending_memories.append(
            {
                "category": category,
                "content": content,
                "confidence": confidence,
                "source_reference": source_reference,
            }
        )


# --- Result envelope ---


@dataclass
class AgentResult:
    """What .run() returns."""

    output: Optional[BaseModel]
    output_valid: bool
    error: Optional[str]
    audit_log_id: int
    memory_ids: list[int]
    model: str
    latency_ms: int
    project_id: Optional[int]


# --- Base class ---


class BaseAgent(ABC):
    """Abstract base for all agents.

    Subclasses declare:
        skill_path: ClassVar[str]  — path to the SKILL.md file (usually __file__)
        output_model: ClassVar[type[BaseModel]]  — Pydantic class for structured output

    And override:
        prepare_input(ctx) -> str  — turn ctx.input into a prompt string
        on_success(ctx, output)    — optional hook after successful validation
    """

    # Subclasses must set these.
    skill_path: ClassVar[str]
    output_model: ClassVar[type[BaseModel]]

    def __init__(self, llm: Optional[LLMClient] = None) -> None:
        self.skill: Skill = load_skill(_skill_md_path_from(self.skill_path))
        self.llm: LLMClient = llm or get_llm_client()

    # --- Hooks subclasses override ---

    @abstractmethod
    def prepare_input(self, ctx: AgentContext) -> str:
        """Return the user-role prompt string. May mutate ctx (e.g. set
        project_id, populate retrieved_source_ids)."""
        ...

    def on_success(self, ctx: AgentContext, output: BaseModel) -> None:
        """Optional post-processing after successful validation. Default: no-op.
        Override to extract memories or trigger side effects."""
        return None

    # --- Framework-owned run pipeline ---

    def run(self, db: Session, input_payload: dict[str, Any]) -> AgentResult:
        """Execute the agent end-to-end.

        Guarantees:
        - Exactly one audit log row is written per call, regardless of outcome.
        - Memories are written after the audit log, so they can reference it.
        - Grounding mode is enforced (strict = refuse without retrieved sources).
        """
        ctx = AgentContext(db=db, input=input_payload)

        # 1. Build the prompt (agent-owned)
        try:
            ctx.prompt = self.prepare_input(ctx)
        except Exception as exc:
            return self._write_audit_and_return(
                ctx,
                output=None,
                error=f"prepare_input failed: {exc}",
                raise_after=True,
            )

        # 2. Enforce grounding policy before we spend an LLM call
        if self.skill.grounding == "strict" and not ctx.retrieved_source_ids:
            return self._write_audit_and_return(
                ctx,
                output=None,
                error=(
                    "Grounding=strict but no sources were retrieved. "
                    "Refusing to call the LLM."
                ),
                raise_after=False,
            )

        # 3. Call the LLM
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
                ctx,
                output=None,
                error=f"LLM call failed: {exc}",
                raise_after=False,
            )

        ctx.llm_output_raw = result.text
        ctx.llm_model = result.model
        ctx.llm_prompt_tokens = result.prompt_tokens
        ctx.llm_completion_tokens = result.completion_tokens
        ctx.llm_latency_ms = int((time.perf_counter() - call_start) * 1000)

        # 4. Validate output against the declared schema
        parsed_output: Optional[BaseModel] = None
        validation_error: Optional[str] = None
        try:
            parsed_json = json.loads(result.text)
            parsed_output = self.output_model.model_validate(parsed_json)
        except (json.JSONDecodeError, ValidationError) as exc:
            validation_error = f"{type(exc).__name__}: {exc}"

        # 5. Write audit log FIRST (so memories can reference its id)
        audit_row = self._write_audit_log(
            ctx,
            output_text=result.text,
            output_valid=parsed_output is not None,
            error=validation_error,
        )
        ctx.audit_log_id = audit_row.id

        if parsed_output is None:
            db.commit()
            return AgentResult(
                output=None,
                output_valid=False,
                error=validation_error,
                audit_log_id=audit_row.id,
                memory_ids=[],
                model=ctx.llm_model or "",
                latency_ms=ctx.llm_latency_ms,
                project_id=ctx.project_id,
            )

        # 6. Success hook (agent-owned)
        try:
            self.on_success(ctx, parsed_output)
        except Exception as exc:
            # Don't fail the whole run because a post-hook failed; log it.
            audit_row.error = f"on_success raised: {exc}"
            db.flush()

        # 7. Persist queued memories
        memory_ids = self._persist_memories(ctx)

        db.commit()

        return AgentResult(
            output=parsed_output,
            output_valid=True,
            error=audit_row.error,
            audit_log_id=audit_row.id,
            memory_ids=memory_ids,
            model=ctx.llm_model or "",
            latency_ms=ctx.llm_latency_ms,
            project_id=ctx.project_id,
        )

    # --- Internal helpers ---

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
            metadata_json={"skill_version": self.skill.version},
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
        """Emergency path when we can't do a normal run (e.g. prepare_input threw)."""
        audit_row = self._write_audit_log(
            ctx,
            output_text=None,
            output_valid=False,
            error=error,
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
        )


# --- Helper ---


def _skill_md_path_from(agent_file: str) -> Path:
    """Given the __file__ of the agent module, return the SKILL.md path."""
    return Path(agent_file).parent / "SKILL.md"