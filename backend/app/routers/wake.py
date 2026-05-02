import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.run import RunResponse
from app.services.run_service import create_activity, get_run

router = APIRouter(prefix="/api/runs", tags=["runs"])

DB = Annotated[AsyncSession, Depends(get_db)]


@router.post("/{run_id}/wake", response_model=RunResponse)
async def wake_run(run_id: uuid.UUID, db: DB) -> RunResponse:
    run = await get_run(db, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    if run.status != "sleeping":
        raise HTTPException(
            status_code=409,
            detail="Run is not sleeping. Use /trigger for active runs or /resume for paused runs.",
        )
    run.status = "active"
    run.wake_at = None
    await create_activity(
        db,
        run_id,
        "system_event",
        {"event": "manual_wake", "reason": "user triggered manual wake"},
    )
    await db.commit()
    await db.refresh(run)
    return run
