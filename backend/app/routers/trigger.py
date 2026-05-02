import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from groq import AsyncGroq
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_groq_client
from app.services.agent_service import trigger_agent

router = APIRouter(prefix="/api/runs", tags=["agent"])

DB = Annotated[AsyncSession, Depends(get_db)]
GroqDep = Annotated[AsyncGroq, Depends(get_groq_client)]


@router.post("/{run_id}/trigger")
async def trigger_run(run_id: uuid.UUID, db: DB, groq: GroqDep) -> dict:
    result = await trigger_agent(run_id, db, groq)
    return {"run_id": str(run_id), **result}
