import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.run import Run
from app.models.supervisor import Supervisor
from app.schemas.supervisor import SupervisorCreate, SupervisorUpdate

_ACTIVE_STATUSES = {"active", "sleeping", "running", "paused"}


async def create_supervisor(db: AsyncSession, data: SupervisorCreate) -> Supervisor:
    supervisor = Supervisor(**data.model_dump())
    db.add(supervisor)
    await db.commit()
    await db.refresh(supervisor)
    return supervisor


async def get_supervisor(db: AsyncSession, supervisor_id: uuid.UUID) -> Supervisor | None:
    result = await db.execute(select(Supervisor).where(Supervisor.id == supervisor_id))
    return result.scalar_one_or_none()


async def list_supervisors(db: AsyncSession) -> list[Supervisor]:
    result = await db.execute(select(Supervisor).order_by(Supervisor.created_at))
    return list(result.scalars().all())


async def update_supervisor(
    db: AsyncSession, supervisor_id: uuid.UUID, data: SupervisorUpdate
) -> Supervisor | None:
    supervisor = await get_supervisor(db, supervisor_id)
    if supervisor is None:
        return None
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(supervisor, field, value)
    await db.commit()
    await db.refresh(supervisor)
    return supervisor


from fastapi import HTTPException

async def has_any_runs(db: AsyncSession, supervisor_id: uuid.UUID) -> bool:
    """Checks if ANY runs exist for this supervisor (historical or active)."""
    result = await db.execute(
        select(Run.id)
        .where(Run.supervisor_id == supervisor_id)
        .limit(1)
    )
    return result.scalar_one_or_none() is not None


async def delete_supervisor(db: AsyncSession, supervisor_id: uuid.UUID) -> bool:
    supervisor = await get_supervisor(db, supervisor_id)
    if supervisor is None:
        return False
    
    if await has_any_runs(db, supervisor_id):
        raise HTTPException(
            status_code=409,
            detail="Cannot delete supervisor with existing runs. Supervisors are retained for historical record."
        )

    await db.delete(supervisor)
    await db.commit()
    return True
