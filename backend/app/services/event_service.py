import uuid
from datetime import datetime, timezone

from fastapi import HTTPException
from groq import AsyncGroq
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.event import EventCreate, EventResponse
from app.services import classifier as classifier_module
from app.services.run_service import create_activity, get_run
from app.services.supervisor_service import get_supervisor


async def ingest_event(
    db: AsyncSession,
    run_id: uuid.UUID,
    event: EventCreate,
    groq_client: AsyncGroq,
) -> EventResponse:
    run = await get_run(db, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")

    if run.status in {"terminated", "completed"}:
        raise HTTPException(status_code=409, detail="Cannot send events to a finished run")

    # 1. Store the incoming event as an activity record
    event_activity = await create_activity(
        db,
        run_id,
        "event_received",
        {"event_type": event.event_type, "data": event.data},
    )

    # 2. Get supervisor for wake_aggressiveness
    supervisor = await get_supervisor(db, run.supervisor_id)
    wake_aggressiveness = supervisor.wake_aggressiveness if supervisor else "normal"

    # 3. Get current order_status from run state
    order_status = run.state.get("order_status", "created")

    # 4. Classify
    should_wake, reason, classifier_layer = await classifier_module.classify_event(
        event_type=event.event_type,
        event_data=event.data,
        order_status=order_status,
        wake_aggressiveness=wake_aggressiveness,
        groq_client=groq_client,
    )

    # 5. Store wake decision activity
    await create_activity(
        db,
        run_id,
        "wake_decision",
        {
            "decision": "wake" if should_wake else "no_wake",
            "reason": reason,
            "event_type": event.event_type,
            "classifier_layer": classifier_layer,
        },
    )

    # 6. If wake decision and run is sleeping, make it active
    if should_wake and run.status == "sleeping":
        run.status = "active"
        run.wake_at = None

    # 7. Append event to state["events_since_last_wake"]
    events_list = list(run.state.get("events_since_last_wake", []))
    events_list.append(
        {
            "event_type": event.event_type,
            "data": event.data,
            "received_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    run.state = {**run.state, "events_since_last_wake": events_list}

    await db.commit()
    await db.refresh(event_activity)

    return EventResponse(
        event_type=event.event_type,
        data=event.data,
        run_id=run_id,
        wake_decision=should_wake,
        wake_reason=reason,
        activity_id=event_activity.id,
        created_at=event_activity.created_at,
    )
