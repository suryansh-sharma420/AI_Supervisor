"""
Integration tests for scheduler job functions.
Job functions are called directly — APScheduler timing is not tested.
execute_agent_cycle is patched so no real LLM calls are made.
"""

import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity import Activity
from app.models.run import Run
from app.scheduler.jobs import enforce_max_run_age, wake_sleeping_runs
from app.services.run_service import get_activities, get_run
from app.services.supervisor_service import create_supervisor
from app.schemas.supervisor import SupervisorCreate
from app.schemas.run import RunCreate
from app.services.run_service import create_run


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_app(session_factory, groq_client=None) -> SimpleNamespace:
    if groq_client is None:
        groq_client = MagicMock()
    state = SimpleNamespace(
        async_session_factory=session_factory,
        groq_client=groq_client,
    )
    return SimpleNamespace(state=state)


async def _make_run(
    db: AsyncSession,
    order_id: str,
    status: str = "sleeping",
    wake_at: datetime | None = None,
    started_at: datetime | None = None,
    max_run_age_hours: int = 168,
) -> Run:
    sup_data = SupervisorCreate(
        name=f"Sched Sup {order_id}",
        base_instruction="Supervise.",
        available_actions=[],
    )
    supervisor = await create_supervisor(db, sup_data)
    run_data = RunCreate(
        supervisor_id=supervisor.id,
        order_id=order_id,
        max_run_age_hours=max_run_age_hours,
    )
    run = await create_run(db, run_data)

    # Adjust fields that create_run doesn't expose
    run.status = status
    run.wake_at = wake_at
    if started_at is not None:
        run.started_at = started_at
    await db.commit()
    await db.refresh(run)
    return run


# ---------------------------------------------------------------------------
# wake_sleeping_runs tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_wake_sleeping_run_past_wake_at(db: AsyncSession, engine) -> None:
    past = datetime.now(timezone.utc) - timedelta(minutes=5)
    run = await _make_run(db, "ORD-SCH-1", status="sleeping", wake_at=past)

    app = _mock_app(engine.get_new_session_factory() if hasattr(engine, "get_new_session_factory") else _session_factory_from_engine(engine))

    cycle_summary = {"slept": True, "sleep_duration_minutes": 60, "actions_taken": [], "iterations": 1, "terminated_early": False}

    with patch("app.scheduler.jobs.execute_agent_cycle", new_callable=AsyncMock, return_value=cycle_summary) as mock_cycle:
        await wake_sleeping_runs(app)

    mock_cycle.assert_called_once()
    called_run_id = mock_cycle.call_args[0][0]
    assert called_run_id == run.id

    # Verify scheduled_wake activity was created
    activities = await get_activities(db, run.id)
    wake_activities = [
        a for a in activities
        if a.activity_type == "system_event" and a.payload.get("event") == "scheduled_wake"
    ]
    assert len(wake_activities) == 1


@pytest.mark.asyncio
async def test_wake_sleeping_run_future_wake_at_not_woken(db: AsyncSession, engine) -> None:
    future = datetime.now(timezone.utc) + timedelta(minutes=60)
    run = await _make_run(db, "ORD-SCH-2", status="sleeping", wake_at=future)

    app = _mock_app(_session_factory_from_engine(engine))

    with patch("app.scheduler.jobs.execute_agent_cycle", new_callable=AsyncMock) as mock_cycle:
        await wake_sleeping_runs(app)

    mock_cycle.assert_not_called()


@pytest.mark.asyncio
async def test_wake_sleeping_run_null_wake_at_not_woken(db: AsyncSession, engine) -> None:
    run = await _make_run(db, "ORD-SCH-3", status="sleeping", wake_at=None)

    app = _mock_app(_session_factory_from_engine(engine))

    with patch("app.scheduler.jobs.execute_agent_cycle", new_callable=AsyncMock) as mock_cycle:
        await wake_sleeping_runs(app)

    mock_cycle.assert_not_called()


@pytest.mark.asyncio
async def test_running_run_not_picked_up(db: AsyncSession, engine) -> None:
    past = datetime.now(timezone.utc) - timedelta(minutes=5)
    run = await _make_run(db, "ORD-SCH-4", status="running", wake_at=past)

    app = _mock_app(_session_factory_from_engine(engine))

    with patch("app.scheduler.jobs.execute_agent_cycle", new_callable=AsyncMock) as mock_cycle:
        await wake_sleeping_runs(app)

    mock_cycle.assert_not_called()


@pytest.mark.asyncio
async def test_multiple_sleeping_runs_all_processed(db: AsyncSession, engine) -> None:
    past = datetime.now(timezone.utc) - timedelta(minutes=5)
    run1 = await _make_run(db, "ORD-SCH-5A", status="sleeping", wake_at=past)
    run2 = await _make_run(db, "ORD-SCH-5B", status="sleeping", wake_at=past)
    run3 = await _make_run(db, "ORD-SCH-5C", status="sleeping", wake_at=past)

    app = _mock_app(_session_factory_from_engine(engine))

    cycle_summary = {"slept": True, "sleep_duration_minutes": 60, "actions_taken": [], "iterations": 1, "terminated_early": False}

    with patch("app.scheduler.jobs.execute_agent_cycle", new_callable=AsyncMock, return_value=cycle_summary) as mock_cycle:
        await wake_sleeping_runs(app)

    assert mock_cycle.call_count == 3


@pytest.mark.asyncio
async def test_one_run_exception_others_still_processed(db: AsyncSession, engine) -> None:
    past = datetime.now(timezone.utc) - timedelta(minutes=5)
    run1 = await _make_run(db, "ORD-SCH-6A", status="sleeping", wake_at=past)
    run2 = await _make_run(db, "ORD-SCH-6B", status="sleeping", wake_at=past)

    app = _mock_app(_session_factory_from_engine(engine))

    call_count = 0

    async def side_effect(run_id, db, groq):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise RuntimeError("Simulated error on first run")
        return {"slept": True, "sleep_duration_minutes": 60, "actions_taken": [], "iterations": 1, "terminated_early": False}

    with patch("app.scheduler.jobs.execute_agent_cycle", side_effect=side_effect):
        await wake_sleeping_runs(app)

    assert call_count == 2


# ---------------------------------------------------------------------------
# enforce_max_run_age tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_expired_run_terminated(db: AsyncSession, engine) -> None:
    old_start = datetime.now(timezone.utc) - timedelta(hours=200)
    run = await _make_run(db, "ORD-SCH-7", status="active", max_run_age_hours=168)
    run.started_at = old_start
    await db.commit()

    app = _mock_app(_session_factory_from_engine(engine))
    await enforce_max_run_age(app)

    await db.refresh(run)
    assert run.status == "terminated"
    assert run.completed_at is not None

    activities = await get_activities(db, run.id)
    # Phase 6: enforce_max_run_age now calls complete_run() which creates
    # a final_output activity (not system_event) with completion_reason
    final_activities = [
        a for a in activities
        if a.activity_type == "final_output"
        and a.payload.get("completion_reason") == "max_run_age_exceeded"
    ]
    assert len(final_activities) == 1


@pytest.mark.asyncio
async def test_non_expired_run_not_terminated(db: AsyncSession, engine) -> None:
    recent_start = datetime.now(timezone.utc) - timedelta(hours=10)
    run = await _make_run(db, "ORD-SCH-8", status="active", max_run_age_hours=168)
    run.started_at = recent_start
    await db.commit()

    app = _mock_app(_session_factory_from_engine(engine))
    await enforce_max_run_age(app)

    await db.refresh(run)
    assert run.status == "active"


@pytest.mark.asyncio
async def test_already_terminated_run_ignored(db: AsyncSession, engine) -> None:
    old_start = datetime.now(timezone.utc) - timedelta(hours=200)
    run = await _make_run(db, "ORD-SCH-9", status="terminated", max_run_age_hours=168)
    run.started_at = old_start
    await db.commit()

    app = _mock_app(_session_factory_from_engine(engine))
    before_activity_count = len(await get_activities(db, run.id))

    await enforce_max_run_age(app)

    after_activity_count = len(await get_activities(db, run.id))
    assert after_activity_count == before_activity_count


@pytest.mark.asyncio
async def test_full_wake_cycle_end_to_end(db: AsyncSession, engine) -> None:
    """Sleeping run wakes, agent sleeps again with new wake_at."""
    import json
    past = datetime.now(timezone.utc) - timedelta(minutes=5)
    run = await _make_run(db, "ORD-SCH-10", status="sleeping", wake_at=past)

    app = _mock_app(_session_factory_from_engine(engine))

    # Mock Groq to call sleep() immediately
    def _tool_call(name, args):
        tc = MagicMock()
        tc.id = f"call_{name}"
        tc.function = MagicMock()
        tc.function.name = name
        tc.function.arguments = json.dumps(args)
        return tc

    def _groq_response(tool_calls):
        message = MagicMock()
        message.content = ""
        message.tool_calls = tool_calls or None
        choice = MagicMock()
        choice.message = message
        resp = MagicMock()
        resp.choices = [choice]
        return resp

    sleep_resp = _groq_response([
        _tool_call("sleep", {
            "duration_minutes": 45,
            "reason": "Waiting for update",
            "next_check_focus": "shipment status",
        })
    ])
    groq = MagicMock()
    groq.chat = MagicMock()
    groq.chat.completions = MagicMock()
    groq.chat.completions.create = AsyncMock(return_value=sleep_resp)

    app.state.groq_client = groq

    await wake_sleeping_runs(app)

    await db.refresh(run)
    assert run.status == "sleeping"
    assert run.wake_at is not None
    assert run.wake_at > datetime.now(timezone.utc)

    activities = await get_activities(db, run.id)
    types = [a.activity_type for a in activities]
    assert "system_event" in types  # scheduled_wake
    assert "sleep_decision" in types

    wake_events = [
        a for a in activities
        if a.activity_type == "system_event" and a.payload.get("event") == "scheduled_wake"
    ]
    assert len(wake_events) == 1


# ---------------------------------------------------------------------------
# Helper: build a session factory from the test engine
# ---------------------------------------------------------------------------

def _session_factory_from_engine(engine):
    from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
    from sqlalchemy.pool import NullPool
    return async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
