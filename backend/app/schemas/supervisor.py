import uuid
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, field_validator, model_validator


class SupervisorCreate(BaseModel):
    name: str
    base_instruction: str
    available_actions: list[str] = [
        "message_fulfillment_team",
        "message_payments_team",
        "message_logistics_team",
        "message_customer",
        "create_internal_note",
    ]
    wake_up_behavior: dict | None = None
    wake_aggressiveness: Literal["conservative", "normal", "aggressive"] = "normal"
    default_sleep_minutes: int = 60
    llm_settings: dict | None = None

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("name must not be empty")
        return v

    @field_validator("base_instruction")
    @classmethod
    def instruction_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("base_instruction must not be empty")
        return v


class SupervisorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    base_instruction: str
    available_actions: list[str]
    wake_up_behavior: dict | None
    wake_aggressiveness: str
    default_sleep_minutes: int
    llm_settings: dict | None
    created_at: datetime
    updated_at: datetime


class SupervisorUpdate(BaseModel):
    name: Optional[str] = None
    base_instruction: Optional[str] = None
    available_actions: Optional[list[str]] = None
    wake_up_behavior: Optional[dict] = None
    wake_aggressiveness: Optional[Literal["conservative", "normal", "aggressive"]] = None
    default_sleep_minutes: Optional[int] = None
    llm_settings: Optional[dict] = None

    @model_validator(mode="after")
    def at_least_one_field(self) -> "SupervisorUpdate":
        provided = {k: v for k, v in self.model_dump().items() if v is not None}
        if not provided:
            raise ValueError("at least one field must be provided")
        return self
