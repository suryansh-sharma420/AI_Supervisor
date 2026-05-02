import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity import Activity
from app.models.run import Run
from app.schemas.run import RunCreate

_DEFAULT_STATE_KEYS = {
    "order_status": "created",
    "agent_summary": "Run initialized. Awaiting first agent cycle.",
    "custom_instructions": [],
    "events_since_last_wake": [],
    "iteration_count": 0,
    "last_action": None,
}


async def create_activity(
    db: AsyncSession, run_id: uuid.UUID, activity_type: str, payload: dict
) -> Activity:
    activity = Activity(run_id=run_id, activity_type=activity_type, payload=payload)
    db.add(activity)
    await db.flush()
    return activity


async def create_run(db: AsyncSession, data: RunCreate) -> Run:
    state = {**_DEFAULT_STATE_KEYS, "order_id": data.order_id}
    state.update(data.initial_state)

    run = Run(
        supervisor_id=data.supervisor_id,
        order_id=data.order_id,
        max_run_age_hours=data.max_run_age_hours,
        state=state,
    )
    db.add(run)
    await db.flush()

    await create_activity(
        db, run.id, "system_event", {"event": "run_started", "order_id": data.order_id}
    )
    await db.commit()
    await db.refresh(run)
    return run


async def get_run(db: AsyncSession, run_id: uuid.UUID) -> Run | None:
    result = await db.execute(select(Run).where(Run.id == run_id))
    return result.scalar_one_or_none()


async def list_runs(
    db: AsyncSession,
    status: str | None = None,
    supervisor_id: uuid.UUID | None = None,
) -> list[Run]:
    q = select(Run).order_by(Run.created_at)
    if status is not None:
        q = q.where(Run.status == status)
    if supervisor_id is not None:
        q = q.where(Run.supervisor_id == supervisor_id)
    result = await db.execute(q)
    return list(result.scalars().all())


async def update_run_status(
    db: AsyncSession, run_id: uuid.UUID, status: str
) -> Run | None:
    run = await get_run(db, run_id)
    if run is None:
        return None
    run.status = status
    await db.commit()
    await db.refresh(run)
    return run


async def add_instruction(
    db: AsyncSession, run_id: uuid.UUID, instruction: str
) -> Run | None:
    run = await get_run(db, run_id)
    if run is None:
        return None
    instructions = list(run.state.get("custom_instructions", []))
    instructions.append(instruction)
    run.state = {**run.state, "custom_instructions": instructions}
    await db.flush()
    await create_activity(db, run_id, "manual_instruction", {"instruction": instruction})
    await db.commit()
    await db.refresh(run)
    return run


async def get_activities(db: AsyncSession, run_id: uuid.UUID) -> list[Activity]:
    result = await db.execute(
        select(Activity)
        .where(Activity.run_id == run_id)
        .order_by(Activity.created_at)
    )
    return list(result.scalars().all())
