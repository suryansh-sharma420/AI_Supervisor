import uuid

from fastapi import HTTPException
from groq import AsyncGroq
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.loop import execute_agent_cycle
from app.services.run_service import get_run


async def trigger_agent(
    run_id: uuid.UUID,
    db: AsyncSession,
    groq_client: AsyncGroq,
) -> dict:
    run = await get_run(db, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    if run.status in {"terminated", "completed"}:
        raise HTTPException(status_code=409, detail="Run is already finished")
    if run.status == "running":
        raise HTTPException(status_code=409, detail="Agent is already running for this run")

    return await execute_agent_cycle(run_id, db, groq_client)
