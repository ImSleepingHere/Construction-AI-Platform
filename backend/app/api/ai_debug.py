"""Temporary debug endpoints for verifying LLM wiring. Remove before submission."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.llm_client import get_llm_client

router = APIRouter(prefix="/debug", tags=["debug"])


class GenerateRequest(BaseModel):
    prompt: str


class GenerateResponse(BaseModel):
    text: str
    model: str
    prompt_tokens: int | None
    completion_tokens: int | None
    latency_ms: int


@router.post("/generate", response_model=GenerateResponse)
def debug_generate(req: GenerateRequest) -> GenerateResponse:
    try:
        result = get_llm_client().generate(req.prompt)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return GenerateResponse(
        text=result.text,
        model=result.model,
        prompt_tokens=result.prompt_tokens,
        completion_tokens=result.completion_tokens,
        latency_ms=result.latency_ms,
    )