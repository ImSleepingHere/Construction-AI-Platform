"""Cron scheduling for agent runs.

Wraps APScheduler's BackgroundScheduler so agents can be registered to run
on a cron schedule (used by the executive_report agent). Each scheduled
invocation opens its own DB session — agent runs must not share a session
across requests/jobs.
"""

from __future__ import annotations

import logging
from typing import Any

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.agents.registry import get_agent
from app.core.database import SessionLocal

logger = logging.getLogger(__name__)


class AgentScheduler:
    def __init__(self) -> None:
        self._scheduler = BackgroundScheduler()

    def register_agent_cron(
        self,
        skill_name: str,
        cron_expr: str,
        input_payload: dict[str, Any],
    ) -> None:
        """Register an agent to run on a cron schedule.

        cron_expr is a standard 5-field cron string ("minute hour day month
        day_of_week"), e.g. "0 8 * * 1" for every Monday at 08:00.
        """
        self._scheduler.add_job(
            self._run_agent,
            trigger=CronTrigger.from_crontab(cron_expr),
            args=[skill_name, input_payload],
            id=f"agent_cron:{skill_name}",
            replace_existing=True,
        )

    def _run_agent(self, skill_name: str, input_payload: dict[str, Any]) -> None:
        with SessionLocal() as db:
            try:
                agent = get_agent(skill_name)
                result = agent.run(db, input_payload)
                logger.info(
                    "scheduled run of %r: output_valid=%s audit_log_id=%s error=%s",
                    skill_name,
                    result.output_valid,
                    result.audit_log_id,
                    result.error,
                )
            except Exception:
                logger.exception("scheduled run of %r failed", skill_name)

    def start(self) -> None:
        self._scheduler.start()

    def shutdown(self) -> None:
        self._scheduler.shutdown(wait=False)


scheduler = AgentScheduler()
