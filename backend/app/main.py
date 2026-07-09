from fastapi import FastAPI

from app.api import projects, suppliers
from app.core.config import settings
from app.api import ai_debug

app = FastAPI(
    title="Construction AI Platform",
    description="AI-powered construction project management platform",
    version="0.1.0",
)

app.include_router(projects.router)
app.include_router(suppliers.router)
app.include_router(ai_debug.router)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "env": settings.APP_ENV,
        "llm_provider": settings.LLM_PROVIDER,
    }


@app.get("/")
def root():
    return {"message": "Construction AI Platform API. See /docs for the API docs."}