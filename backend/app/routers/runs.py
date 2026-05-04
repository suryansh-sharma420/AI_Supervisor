import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from groq import AsyncGroq
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_groq_client
from app.schemas.run import ActivityResponse, InstructionRequest, RunCreate, RunResponse
from app.services import run_service, supervisor_service
from app.services.summary_service import complete_run

router = APIRouter(prefix="/api/runs", tags=["runs"])

DB = Annotated[AsyncSession, Depends(get_db)]
GroqDep = Annotated[AsyncGroq, Depends(get_groq_client)]

_INTERRUPTIBLE = {"active", "running", "sleeping"}


@router.post("", response_model=RunResponse, status_code=status.HTTP_201_CREATED)
async def create_run(body: RunCreate, db: DB) -> RunResponse:
    supervisor = await supervisor_service.get_supervisor(db, body.supervisor_id)
    if supervisor is None:
        raise HTTPException(status_code=404, detail="Supervisor not found")
    return await run_service.create_run(db, body)


@router.get("", response_model=list[RunResponse])
async def list_runs(
    db: DB,
    status: str | None = Query(default=None),
    supervisor_id: uuid.UUID | None = Query(default=None),
) -> list[RunResponse]:
    return await run_service.list_runs(db, status=status, supervisor_id=supervisor_id)


@router.get("/{run_id}", response_model=RunResponse)
async def get_run(run_id: uuid.UUID, db: DB) -> RunResponse:
    run = await run_service.get_run(db, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@router.post("/{run_id}/instructions", response_model=RunResponse)
async def add_instruction(run_id: uuid.UUID, body: InstructionRequest, db: DB) -> RunResponse:
    run = await run_service.get_run(db, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return await run_service.add_instruction(db, run_id, body.instruction)


@router.delete("/{run_id}/instructions/{index}", response_model=RunResponse)
async def remove_instruction(run_id: uuid.UUID, index: int, db: DB) -> RunResponse:
    run = await run_service.get_run(db, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    res = await run_service.remove_instruction(db, run_id, index)
    if res is None:
        raise HTTPException(status_code=404, detail="Instruction not found")
    return res


@router.post("/{run_id}/interrupt", response_model=RunResponse)
async def interrupt_run(run_id: uuid.UUID, db: DB) -> RunResponse:
    run = await run_service.get_run(db, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    if run.status not in _INTERRUPTIBLE:
        raise HTTPException(status_code=409, detail="Run is not in an interruptible state")
    run.status = "paused"
    await db.commit()
    await db.refresh(run)
    await run_service.create_activity(db, run_id, "system_event", {"event": "run_paused"})
    await db.commit()
    await db.refresh(run)
    return run


@router.post("/{run_id}/resume", response_model=RunResponse)
async def resume_run(run_id: uuid.UUID, db: DB) -> RunResponse:
    run = await run_service.get_run(db, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    if run.status != "paused":
        raise HTTPException(status_code=409, detail="Run is not paused")
    run.status = "active"
    run.wake_at = None
    await db.commit()
    await db.refresh(run)
    await run_service.create_activity(db, run_id, "system_event", {"event": "run_resumed"})
    await db.commit()
    await db.refresh(run)
    return run


@router.post("/{run_id}/terminate", response_model=RunResponse)
async def terminate_run(run_id: uuid.UUID, db: DB, groq: GroqDep) -> RunResponse:
    run = await run_service.get_run(db, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    if run.status in {"terminated", "completed"}:
        raise HTTPException(status_code=409, detail="Run is already finished")
    return await complete_run(run, db, groq, reason="manual_termination", final_status="terminated")


@router.get("/{run_id}/activities", response_model=list[ActivityResponse])
async def get_activities(run_id: uuid.UUID, db: DB) -> list[ActivityResponse]:
    run = await run_service.get_run(db, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return await run_service.get_activities(db, run_id)
