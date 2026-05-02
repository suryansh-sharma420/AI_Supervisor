from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.scheduler import jobs

scheduler = AsyncIOScheduler()


def start_scheduler(app) -> None:
    scheduler.add_job(
        jobs.wake_sleeping_runs,
        trigger="interval",
        seconds=60,
        id="wake_sleeping_runs",
        replace_existing=True,
        kwargs={"app": app},
    )
    scheduler.add_job(
        jobs.enforce_max_run_age,
        trigger="interval",
        seconds=300,
        id="enforce_max_run_age",
        replace_existing=True,
        kwargs={"app": app},
    )
    scheduler.start()


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
