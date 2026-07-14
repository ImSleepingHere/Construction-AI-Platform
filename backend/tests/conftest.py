"""Shared pytest fixtures.

No separate test database: db_session runs each test inside a SAVEPOINT
(nested transaction) on the real Postgres connection, and rolls it back
afterward. Application code under test (BaseAgent, tool functions) can call
session.commit() freely -- that only releases the SAVEPOINT, not the outer
transaction, thanks to the after_transaction_end listener restarting a new
one. See "Joining a Session into an External Transaction" in the SQLAlchemy
docs for the pattern this follows.
"""

from __future__ import annotations

from typing import Optional

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event

from app.core.database import SessionLocal, engine, get_db
from app.main import app
from app.services.llm_client import LLMClient, LLMResult


@pytest.fixture
def db_session():
    connection = engine.connect()
    trans = connection.begin()
    session = SessionLocal(bind=connection)

    session.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def _restart_savepoint(sess, transaction):
        if not connection.in_nested_transaction():
            connection.begin_nested()

    yield session

    session.close()
    trans.rollback()
    connection.close()


@pytest.fixture
def client(db_session):
    """TestClient wired to db_session via dependency override.

    Deliberately instantiated without `with TestClient(app) as c:` --  that
    would run FastAPI's ASGI lifespan (startup/shutdown), which starts the
    real APScheduler and registers a real cron job. Plain instantiation
    skips lifespan entirely, which is what we want for endpoint tests (none
    of the tested endpoints depend on startup-time state).
    """

    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()


class FakeLLMClient(LLMClient):
    """Canned-response double for LLMClient. Never touches the network.

    Construct with a list of LLMResult to return in order (one per call to
    generate()); once exhausted, falls back to a default empty-JSON result.
    generate_calls/embed_calls record every call for assertions.
    """

    def __init__(self, responses: Optional[list[LLMResult]] = None) -> None:
        self._responses = list(responses) if responses else []
        self._default_model = "fake-model"
        self.generate_calls: list[dict] = []
        self.embed_calls: list[str] = []

    def generate(
        self,
        prompt: str,
        *,
        model: Optional[str] = None,
        system_instruction: Optional[str] = None,
        response_schema=None,
        temperature: float = 0.2,
        max_output_tokens: Optional[int] = None,
        tools: Optional[list[dict]] = None,
        conversation: Optional[list[dict]] = None,
    ) -> LLMResult:
        self.generate_calls.append(
            {
                "prompt": prompt,
                "system_instruction": system_instruction,
                "response_schema": response_schema,
                "tools": tools,
                "conversation": list(conversation) if conversation else None,
            }
        )
        if self._responses:
            return self._responses.pop(0)
        return LLMResult(text="{}", model=self._default_model)

    def embed(self, text: str, *, model: Optional[str] = None) -> list[float]:
        self.embed_calls.append(text)
        return [0.01] * 768


@pytest.fixture
def mock_llm() -> FakeLLMClient:
    return FakeLLMClient()
