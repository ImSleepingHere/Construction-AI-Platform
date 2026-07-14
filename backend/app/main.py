from fastapi import FastAPI

from app.api import projects, suppliers
from app.core.config import settings
from app.api import ai_debug
from app.api import agents
from app.api import approvals
from app.services.scheduler import scheduler


app = FastAPI(
    title="Construction AI Platform",
    description="AI-powered construction project management platform",
    version="0.1.0",
)

app.include_router(projects.router)
app.include_router(suppliers.router)
app.include_router(ai_debug.router)
app.include_router(agents.router)
app.include_router(approvals.router)


@app.on_event("startup")
def _start_scheduler() -> None:
    scheduler.start()
    # Every Monday at 09:00 UTC.
    scheduler.register_agent_cron("executive_report", "0 9 * * 1", {})


@app.on_event("shutdown")
def _stop_scheduler() -> None:
    scheduler.shutdown()

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