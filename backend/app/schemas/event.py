import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class EventCreate(BaseModel):
    event_type: Literal[
        "order_created",
        "payment_confirmed",
        "payment_failed",
        "shipment_created",
        "shipment_delayed",
        "delivered",
        "refund_requested",
        "customer_message_received",
        "no_update_for_n_hours",
    ]
    data: dict = {}


class EventResponse(BaseModel):
    event_type: str
    data: dict
    run_id: uuid.UUID
    wake_decision: bool
    wake_reason: str
    activity_id: uuid.UUID
    created_at: datetime
