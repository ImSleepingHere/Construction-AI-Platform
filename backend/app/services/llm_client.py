"""
LLM client abstraction.

Every workflow calls Gemini (or any future provider) through this interface.
Handles:
- retries with exponential backoff
- token usage tracking
- latency measurement
- structured output via response_schema
- tool calling (function calling) for agent loops
"""

from __future__ import annotations

import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from google import genai
from google.genai import types as genai_types
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings


class GroundingMode(str, Enum):
    STRICT = "strict"
    LENIENT = "lenient"
    OFF = "off"


@dataclass
class ToolCall:
    """A tool call the LLM wants us to execute."""
    name: str
    arguments: dict[str, Any]
    call_id: str = ""


@dataclass
class LLMResult:
    """Standardized result from any LLM call."""
    text: str
    model: str
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    latency_ms: int = 0
    raw_response: Any = None
    tool_calls: list[ToolCall] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    # For tool-calling loops: the model's full response Content, to be
    # appended verbatim to conversation history so thought_signatures and
    # other SDK-managed fields survive the round trip.
    response_content: Any = None


@dataclass
class ToolCall:
    """A tool call the LLM wants us to execute."""
    name: str
    arguments: dict[str, Any]
    call_id: str = ""
    thought_signature: Optional[bytes] = None


class LLMClient(ABC):
    """Provider-agnostic interface."""

    @abstractmethod
    def generate(
        self,
        prompt: str,
        *,
        model: Optional[str] = None,
        system_instruction: Optional[str] = None,
        response_schema: Any = None,
        temperature: float = 0.2,
        max_output_tokens: Optional[int] = None,
        tools: Optional[list[dict]] = None,
        conversation: Optional[list[dict]] = None,
    ) -> LLMResult: ...

    @abstractmethod
    def embed(self, text: str, *, model: Optional[str] = None) -> list[float]: ...


class GeminiClient(LLMClient):
    def __init__(
        self,
        api_key: Optional[str] = None,
        default_model: Optional[str] = None,
        default_embedding_model: Optional[str] = None,
    ) -> None:
        self._client = genai.Client(api_key=api_key or settings.GEMINI_API_KEY)
        self._default_model = default_model or settings.GEMINI_MODEL
        self._default_embedding_model = (
            default_embedding_model or settings.GEMINI_EMBEDDING_MODEL
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        reraise=True,
    )
    def generate(
        self,
        prompt: str,
        *,
        model: Optional[str] = None,
        system_instruction: Optional[str] = None,
        response_schema: Any = None,
        temperature: float = 0.2,
        max_output_tokens: Optional[int] = None,
        tools: Optional[list[dict]] = None,
        conversation: Optional[list[dict]] = None,
    ) -> LLMResult:
        chosen_model = model or self._default_model

        config_kwargs: dict[str, Any] = {"temperature": temperature}
        if system_instruction:
            config_kwargs["system_instruction"] = system_instruction
        if max_output_tokens:
            config_kwargs["max_output_tokens"] = max_output_tokens
        if response_schema is not None and not tools:
            # Structured output mode. Only for final-response calls (no tools).
            config_kwargs["response_mime_type"] = "application/json"
            config_kwargs["response_schema"] = response_schema
        if tools:
            # Function calling mode. Gemini's SDK accepts a list of tool declarations.
            config_kwargs["tools"] = [
                genai_types.Tool(function_declarations=[
                    genai_types.FunctionDeclaration(
                        name=t["name"],
                        description=t["description"],
                        parameters=t["parameters"],
                    )
                    for t in tools
                ])
            ]

        config = genai_types.GenerateContentConfig(**config_kwargs)

        # Contents = conversation history + this turn's prompt (if any).
        contents: list[Any] = list(conversation or [])
        if prompt:
            contents.append(prompt)

        start = time.perf_counter()
        response = self._client.models.generate_content(
            model=chosen_model,
            contents=contents,
            config=config,
        )
        latency_ms = int((time.perf_counter() - start) * 1000)

        # Extract usage, text, and tool calls.
        usage = getattr(response, "usage_metadata", None)
        prompt_tokens = getattr(usage, "prompt_token_count", None) if usage else None
        completion_tokens = getattr(usage, "candidates_token_count", None) if usage else None

        tool_calls: list[ToolCall] = []
        text_out = ""

        candidates = getattr(response, "candidates", None) or []
        response_content = None
        if candidates:
            content = getattr(candidates[0], "content", None)
            response_content = content  # capture for verbatim echo in tool loops
            parts = getattr(content, "parts", None) or []
            for i, part in enumerate(parts):
                fn = getattr(part, "function_call", None)
                if fn is not None:
                    args = dict(fn.args) if fn.args else {}
                    # Preserve thought signature for Gemini 3.x thinking models.
                    # Required when we echo this call back in conversation history.
                    thought_sig = getattr(part, "thought_signature", None)
                    tool_calls.append(ToolCall(
                        name=fn.name,
                        arguments=args,
                        call_id=f"call_{i}",
                        thought_signature=thought_sig,
                    ))
                else:
                    text_part = getattr(part, "text", None)
                    if text_part:
                        text_out += text_part

        # Fall back to response.text if we didn't collect any parts.
        if not text_out and not tool_calls:
            text_out = getattr(response, "text", "") or ""

        return LLMResult(
            text=text_out,
            model=chosen_model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=latency_ms,
            raw_response=response,
            tool_calls=tool_calls,
            response_content=response_content,
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        reraise=True,
    )
    def embed(self, text: str, *, model: Optional[str] = None) -> list[float]:
        chosen_model = model or self._default_embedding_model
        response = self._client.models.embed_content(
            model=chosen_model,
            contents=text,
        )
        return list(response.embeddings[0].values)


_llm_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    global _llm_client
    if _llm_client is None:
        _llm_client = GeminiClient()
    return _llm_client