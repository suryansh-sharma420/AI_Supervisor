import uuid
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, field_validator


class RunCreate(BaseModel):
    supervisor_id: uuid.UUID
    order_id: str
    max_run_age_hours: int = 168
    initial_state: dict = {}

    @field_validator("order_id")
    @classmethod
    def order_id_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("order_id must not be empty")
        return v


class RunResponse(BaseModel):
    id: uuid.UUID
    supervisor_id: uuid.UUID
    order_id: str
    status: str
    state: dict
    wake_at: datetime | None
    started_at: datetime
    completed_at: datetime | None
    max_run_age_hours: int
    final_summary: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RunStatusUpdate(BaseModel):
    status: Literal["active", "sleeping", "running", "paused", "completed", "terminated"]


class ActivityResponse(BaseModel):
    id: uuid.UUID
    run_id: uuid.UUID
    activity_type: str
    payload: dict
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InstructionRequest(BaseModel):
    instruction: str
