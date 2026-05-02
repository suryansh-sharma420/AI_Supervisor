import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from groq import AsyncGroq
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_groq_client
from app.schemas.event import EventCreate, EventResponse
from app.services.event_service import ingest_event

router = APIRouter(prefix="/api/runs", tags=["events"])

DB = Annotated[AsyncSession, Depends(get_db)]
GroqDep = Annotated[AsyncGroq, Depends(get_groq_client)]


@router.post("/{run_id}/events", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
async def post_event(run_id: uuid.UUID, body: EventCreate, db: DB, groq: GroqDep) -> EventResponse:
    return await ingest_event(db, run_id, body, groq)
