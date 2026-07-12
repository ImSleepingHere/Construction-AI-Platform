"""
LLM client abstraction.

Every workflow calls Gemini (or any future provider) through this interface.
That means:
- Provider swap is one class, not one hundred call sites.
- Retries, timeouts, cost accounting, and audit hooks live in one place.
- Grounding policy is applied uniformly.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from google import genai
from google.genai import types as genai_types
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings


class GroundingMode(str, Enum):
    """How the workflow expects the LLM to behave when evidence is thin."""

    STRICT = "strict"      # Refuse to answer if no sources retrieved.
    LENIENT = "lenient"    # Answer but flag as low-confidence.
    OFF = "off"            # Grounding not applicable (e.g. pure generation).


@dataclass
class LLMResult:
    """Standardized result from any LLM call, for logging and downstream use."""

    text: str
    model: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    latency_ms: int = 0
    raw_response: Any = None
    metadata: dict[str, Any] = field(default_factory=dict)


class LLMClient(ABC):
    """Provider-agnostic interface. All AI calls go through this."""

    @abstractmethod
    def generate(
        self,
        prompt: str,
        *,
        model: str | None = None,
        system_instruction: str | None = None,
        response_schema: Any = None,
        temperature: float = 0.2,
        max_output_tokens: int | None = None,
    ) -> LLMResult:
        ...

    @abstractmethod
    def embed(self, text: str, *, model: str | None = None) -> list[float]:
        ...


class GeminiClient(LLMClient):
    """Gemini implementation of LLMClient."""

    def __init__(
        self,
        api_key: str | None = None,
        default_model: str | None = None,
        default_embedding_model: str | None = None,
    ):
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
        model: str | None = None,
        system_instruction: str | None = None,
        response_schema: dict | None = None,
        temperature: float = 0.2,
        max_output_tokens: int | None = None,
    ) -> LLMResult:
        chosen_model = model or self._default_model

        config_kwargs: dict[str, Any] = {"temperature": temperature}
        if system_instruction:
            config_kwargs["system_instruction"] = system_instruction
        if max_output_tokens:
            config_kwargs["max_output_tokens"] = max_output_tokens
        if response_schema:
            config_kwargs["response_mime_type"] = "application/json"
            config_kwargs["response_schema"] = response_schema

        config = genai_types.GenerateContentConfig(**config_kwargs)

        start = time.perf_counter()
        response = self._client.models.generate_content(
            model=chosen_model,
            contents=prompt,
            config=config,
        )
        latency_ms = int((time.perf_counter() - start) * 1000)

        usage = getattr(response, "usage_metadata", None)
        prompt_tokens = getattr(usage, "prompt_token_count", None) if usage else None
        completion_tokens = (
            getattr(usage, "candidates_token_count", None) if usage else None
        )

        return LLMResult(
            text=response.text or "",
            model=chosen_model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=latency_ms,
            raw_response=response,
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        reraise=True,
    )
    def embed(self, text: str, *, model: str | None = None) -> list[float]:
        chosen_model = model or self._default_embedding_model
        response = self._client.models.embed_content(
            model=chosen_model,
            contents=text,
        )
        return list(response.embeddings[0].values)


# Single shared instance the app uses. Instantiate lazily so tests can patch it.
_llm_client: LLMClient | None = None


def get_llm_client() -> LLMClient:
    global _llm_client
    if _llm_client is None:
        _llm_client = GeminiClient()
    return _llm_client