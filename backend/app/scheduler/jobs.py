import logging
from datetime import datetime, timezone

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.loop import execute_agent_cycle
from app.services.run_service import create_activity

logger = logging.getLogger(__name__)


async def wake_sleeping_runs(app) -> None:
    logger.info("Scheduler: checking for sleeping runs")
    now = datetime.now(timezone.utc)
    processed = 0

    async with app.state.async_session_factory() as db:
        from app.models.run import Run

        result = await db.execute(
            select(Run).where(
                Run.status == "sleeping",
                Run.wake_at.is_not(None),
                Run.wake_at <= now,
            )
        )
        runs = result.scalars().all()

    for run in runs:
        try:
            async with app.state.async_session_factory() as db:
                from app.models.run import Run as RunModel

                result = await db.execute(
                    select(RunModel).where(RunModel.id == run.id)
                )
                fresh_run = result.scalar_one_or_none()
                if fresh_run is None or fresh_run.status != "sleeping":
                    continue

                logger.info(
                    "Scheduler: waking run %s, order %s",
                    fresh_run.id,
                    fresh_run.order_id,
                )
                fresh_run.status = "active"
                await create_activity(
                    db,
                    fresh_run.id,
                    "system_event",
                    {
                        "event": "scheduled_wake",
                        "scheduled_for": fresh_run.wake_at.isoformat()
                        if fresh_run.wake_at
                        else None,
                    },
                )
                await db.commit()

            async with app.state.async_session_factory() as db:
                await execute_agent_cycle(run.id, db, app.state.groq_client)

            processed += 1
        except Exception as exc:
            logger.warning("Scheduler: error processing run %s: %s", run.id, exc)

    logger.info("Scheduler: %d runs processed this cycle", processed)


async def enforce_max_run_age(app) -> None:
    logger.info("Scheduler: checking for expired runs")
    now = datetime.now(timezone.utc)

    async with app.state.async_session_factory() as db:
        from app.models.run import Run

        result = await db.execute(
            select(Run).where(
                Run.status.not_in(["completed", "terminated"]),
                text(
                    "runs.started_at + runs.max_run_age_hours * interval '1 hour' <= :now"
                ).bindparams(now=now),
            )
        )
        runs = result.scalars().all()

    for run in runs:
        try:
            async with app.state.async_session_factory() as db:
                from app.models.run import Run as RunModel
                from app.services.summary_service import complete_run

                result = await db.execute(
                    select(RunModel).where(RunModel.id == run.id)
                )
                fresh_run = result.scalar_one_or_none()
                if fresh_run is None or fresh_run.status in {"completed", "terminated"}:
                    continue

                logger.info("Scheduler: terminated expired run %s", fresh_run.id)
                await complete_run(
                    fresh_run,
                    db,
                    app.state.groq_client,
                    reason="max_run_age_exceeded",
                    final_status="terminated",
                )
        except Exception as exc:
            logger.warning("Scheduler: error terminating run %s: %s", run.id, exc)
