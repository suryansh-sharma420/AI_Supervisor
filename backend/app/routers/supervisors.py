import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.supervisor import SupervisorCreate, SupervisorResponse, SupervisorUpdate
from app.services import supervisor_service

router = APIRouter(prefix="/api/supervisors", tags=["supervisors"])

DB = Annotated[AsyncSession, Depends(get_db)]


@router.post("", response_model=SupervisorResponse, status_code=status.HTTP_201_CREATED)
async def create_supervisor(body: SupervisorCreate, db: DB) -> SupervisorResponse:
    return await supervisor_service.create_supervisor(db, body)


@router.get("", response_model=list[SupervisorResponse])
async def list_supervisors(db: DB) -> list[SupervisorResponse]:
    return await supervisor_service.list_supervisors(db)


@router.get("/{supervisor_id}", response_model=SupervisorResponse)
async def get_supervisor(supervisor_id: uuid.UUID, db: DB) -> SupervisorResponse:
    supervisor = await supervisor_service.get_supervisor(db, supervisor_id)
    if supervisor is None:
        raise HTTPException(status_code=404, detail="Supervisor not found")
    return supervisor


@router.patch("/{supervisor_id}", response_model=SupervisorResponse)
async def update_supervisor(
    supervisor_id: uuid.UUID, body: SupervisorUpdate, db: DB
) -> SupervisorResponse:
    supervisor = await supervisor_service.update_supervisor(db, supervisor_id, body)
    if supervisor is None:
        raise HTTPException(status_code=404, detail="Supervisor not found")
    return supervisor


@router.delete("/{supervisor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_supervisor(supervisor_id: uuid.UUID, db: DB) -> None:
    success = await supervisor_service.delete_supervisor(db, supervisor_id)
    if not success:
        raise HTTPException(status_code=404, detail="Supervisor not found")
