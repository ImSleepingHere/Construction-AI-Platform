from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import projects, suppliers
from app.core.config import settings
from app.api import ai_debug
from app.api import agents
from app.api import approvals
from app.api import audit_logs
from app.api import chat
from app.api import metrics
from app.services.scheduler import scheduler


app = FastAPI(
    title="Construction AI Platform",
    description="AI-powered construction project management platform",
    version="0.1.0",
)

# Dev-only: allow the Next.js frontend (localhost:3000) to call the API
# directly from the browser. Tighten this before any real deployment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects.router)
app.include_router(suppliers.router)
app.include_router(ai_debug.router)
app.include_router(agents.router)
app.include_router(approvals.router)
app.include_router(audit_logs.router)
app.include_router(chat.router)
app.include_router(metrics.router)


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