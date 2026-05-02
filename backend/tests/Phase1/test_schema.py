import uuid
from datetime import datetime, timezone

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.models.activity import Activity
from app.models.run import Run
from app.models.supervisor import Supervisor


@pytest.mark.asyncio
async def test_all_tables_exist(db: AsyncSession) -> None:
    result = await db.execute(
        text(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name IN ('supervisors', 'runs', 'activities')"
        )
    )
    tables = {row[0] for row in result.fetchall()}
    assert tables == {"supervisors", "runs", "activities"}


@pytest.mark.asyncio
async def test_insert_supervisor(db: AsyncSession) -> None:
    supervisor = Supervisor(
        name="Test Supervisor",
        base_instruction="Monitor orders carefully.",
        available_actions=["notify_customer", "escalate"],
        wake_up_behavior={"default_sleep_minutes": 60},
        wake_aggressiveness="aggressive",
        llm_settings={"model": "llama3-8b-8192", "temperature": 0.3},
    )
    db.add(supervisor)
    await db.commit()
    await db.refresh(supervisor)

    assert supervisor.id is not None
    assert supervisor.name == "Test Supervisor"
    assert supervisor.base_instruction == "Monitor orders carefully."
    assert supervisor.available_actions == ["notify_customer", "escalate"]
    assert supervisor.wake_up_behavior == {"default_sleep_minutes": 60}
    assert supervisor.wake_aggressiveness == "aggressive"
    assert supervisor.llm_settings == {"model": "llama3-8b-8192", "temperature": 0.3}
    assert supervisor.created_at is not None
    assert supervisor.updated_at is not None


@pytest.mark.asyncio
async def test_insert_run_with_fk(db: AsyncSession) -> None:
    supervisor = Supervisor(
        name="FK Supervisor",
        base_instruction="Track shipments.",
        available_actions=[],
    )
    db.add(supervisor)
    await db.commit()
    await db.refresh(supervisor)

    run = Run(
        supervisor_id=supervisor.id,
        order_id="ORD-001",
        status="active",
        state={"iteration_count": 0, "last_action": None},
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)

    assert run.id is not None
    assert run.supervisor_id == supervisor.id
    assert run.order_id == "ORD-001"
    assert run.status == "active"
    assert run.max_run_age_hours == 168


@pytest.mark.asyncio
async def test_insert_activity_with_fk(db: AsyncSession) -> None:
    supervisor = Supervisor(
        name="Activity Supervisor",
        base_instruction="Log all events.",
        available_actions=[],
    )
    db.add(supervisor)
    await db.commit()
    await db.refresh(supervisor)

    run = Run(supervisor_id=supervisor.id, order_id="ORD-002", state={})
    db.add(run)
    await db.commit()
    await db.refresh(run)

    activity = Activity(
        run_id=run.id,
        activity_type="event_received",
        payload={"event_type": "payment_failed", "data": {"amount": 99.99}},
    )
    db.add(activity)
    await db.commit()
    await db.refresh(activity)

    assert activity.id is not None
    assert activity.run_id == run.id
    assert activity.activity_type == "event_received"
    assert activity.payload["event_type"] == "payment_failed"


@pytest.mark.asyncio
async def test_run_status_not_db_constrained(db: AsyncSession) -> None:
    """
    Status values (active, sleeping, running, paused, completed, terminated)
    are enforced at the application layer, not via a DB CHECK constraint.
    The DB accepts any VARCHAR(50) value.
    """
    supervisor = Supervisor(
        name="Status Supervisor",
        base_instruction="Test status.",
        available_actions=[],
    )
    db.add(supervisor)
    await db.commit()
    await db.refresh(supervisor)

    run = Run(supervisor_id=supervisor.id, order_id="ORD-003", status="custom_value", state={})
    db.add(run)
    await db.commit()
    await db.refresh(run)

    assert run.status == "custom_value"


@pytest.mark.asyncio
async def test_supervisor_delete_raises_fk_error(db: AsyncSession) -> None:
    """Deleting a supervisor with existing runs raises an IntegrityError (no cascade delete)."""
    from sqlalchemy.exc import IntegrityError

    supervisor = Supervisor(
        name="Delete Me",
        base_instruction="Will be deleted.",
        available_actions=[],
    )
    db.add(supervisor)
    await db.commit()
    await db.refresh(supervisor)

    run = Run(supervisor_id=supervisor.id, order_id="ORD-004", state={})
    db.add(run)
    await db.commit()

    with pytest.raises(IntegrityError):
        await db.delete(supervisor)
        await db.commit()

    await db.rollback()


@pytest.mark.asyncio
async def test_wake_at_nullable_and_settable(db: AsyncSession) -> None:
    supervisor = Supervisor(
        name="Wake Supervisor",
        base_instruction="Sleep and wake.",
        available_actions=[],
    )
    db.add(supervisor)
    await db.commit()
    await db.refresh(supervisor)

    run = Run(supervisor_id=supervisor.id, order_id="ORD-005", state={})
    db.add(run)
    await db.commit()
    await db.refresh(run)

    assert run.wake_at is None

    wake_time = datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
    run.wake_at = wake_time
    await db.commit()
    await db.refresh(run)
    assert run.wake_at is not None

    run.wake_at = None
    await db.commit()
    await db.refresh(run)
    assert run.wake_at is None


@pytest.mark.asyncio
async def test_state_jsonb_nested(db: AsyncSession) -> None:
    supervisor = Supervisor(
        name="JSONB Supervisor",
        base_instruction="Test JSON.",
        available_actions=[],
    )
    db.add(supervisor)
    await db.commit()
    await db.refresh(supervisor)

    nested_state = {
        "order_status": "shipped",
        "last_action": "notify_customer",
        "agent_summary": "Package en route",
        "events_since_last_wake": [{"type": "status_update", "data": {"carrier": "FedEx"}}],
        "iteration_count": 3,
    }
    run = Run(supervisor_id=supervisor.id, order_id="ORD-006", state=nested_state)
    db.add(run)
    await db.commit()
    await db.refresh(run)

    assert run.state["order_status"] == "shipped"
    assert run.state["events_since_last_wake"][0]["data"]["carrier"] == "FedEx"
    assert run.state["iteration_count"] == 3


@pytest.mark.asyncio
async def test_health_endpoint() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "environment" in data
