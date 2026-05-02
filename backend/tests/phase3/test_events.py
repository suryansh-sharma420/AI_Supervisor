import json
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_groq_client
from app.main import app


def _make_groq_mock(decision: str = "wake", reason: str = "test reason") -> MagicMock:
    message = MagicMock()
    message.content = json.dumps({"decision": decision, "reason": reason})
    choice = MagicMock()
    choice.message = message
    completion = MagicMock()
    completion.choices = [choice]
    groq = MagicMock()
    groq.chat = MagicMock()
    groq.chat.completions = MagicMock()
    groq.chat.completions.create = AsyncMock(return_value=completion)
    return groq


def _override_groq(mock: MagicMock) -> None:
    app.dependency_overrides[get_groq_client] = lambda: mock


def _clear_overrides() -> None:
    app.dependency_overrides.pop(get_groq_client, None)


async def _make_supervisor_and_run(client: AsyncClient, order_id: str = "ORD-EVT") -> tuple[str, str]:
    sup_resp = await client.post(
        "/api/supervisors",
        json={"name": f"Event Sup {order_id}", "base_instruction": "Handle events."},
    )
    sup_id = sup_resp.json()["id"]
    run_resp = await client.post(
        "/api/runs",
        json={"supervisor_id": sup_id, "order_id": order_id},
    )
    return sup_id, run_resp.json()["id"]


@pytest.mark.asyncio
async def test_post_event_to_active_run_creates_activities(db: AsyncSession) -> None:
    mock_groq = _make_groq_mock("wake", "order created needs attention")
    _override_groq(mock_groq)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            _, run_id = await _make_supervisor_and_run(client, "ORD-EVT-1")
            resp = await client.post(
                f"/api/runs/{run_id}/events",
                json={"event_type": "order_created", "data": {}},
            )
        assert resp.status_code == 201
        data = resp.json()
        assert data["event_type"] == "order_created"
        assert "wake_decision" in data
        assert "wake_reason" in data
        assert "activity_id" in data
    finally:
        _clear_overrides()


@pytest.mark.asyncio
async def test_critical_event_on_sleeping_run_wakes_it(db: AsyncSession) -> None:
    _override_groq(_make_groq_mock())  # won't be called for critical events
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            _, run_id = await _make_supervisor_and_run(client, "ORD-EVT-2")
            # Put run to sleep
            await client.post(f"/api/runs/{run_id}/interrupt")
            # Manually set to sleeping via a direct status — use terminate+create workaround:
            # Actually just use the runs endpoint to check; we set it sleeping via DB
            # Simpler: interrupt sets paused, but spec says sleeping runs get woken.
            # Use a fresh run that we'll manually put to sleeping status via DB.
            from app.services.run_service import get_run, update_run_status
            run = await get_run(db, uuid.UUID(run_id))
            run.status = "sleeping"
            await db.commit()

            resp = await client.post(
                f"/api/runs/{run_id}/events",
                json={"event_type": "payment_failed", "data": {}},
            )
        assert resp.status_code == 201
        assert resp.json()["wake_decision"] is True

        run = await get_run(db, uuid.UUID(run_id))
        await db.refresh(run)
        assert run.status == "active"
    finally:
        _clear_overrides()


@pytest.mark.asyncio
async def test_non_urgent_event_on_sleeping_run_stays_sleeping(db: AsyncSession) -> None:
    _override_groq(_make_groq_mock())
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            _, run_id = await _make_supervisor_and_run(client, "ORD-EVT-3")
            from app.services.run_service import get_run
            run = await get_run(db, uuid.UUID(run_id))
            run.status = "sleeping"
            await db.commit()

            resp = await client.post(
                f"/api/runs/{run_id}/events",
                json={"event_type": "shipment_created", "data": {}},
            )
        assert resp.status_code == 201
        assert resp.json()["wake_decision"] is False

        run = await get_run(db, uuid.UUID(run_id))
        await db.refresh(run)
        assert run.status == "sleeping"
    finally:
        _clear_overrides()


@pytest.mark.asyncio
async def test_event_to_terminated_run_returns_409(db: AsyncSession) -> None:
    _override_groq(_make_groq_mock())
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            _, run_id = await _make_supervisor_and_run(client, "ORD-EVT-4")
            await client.post(f"/api/runs/{run_id}/terminate")
            resp = await client.post(
                f"/api/runs/{run_id}/events",
                json={"event_type": "order_created", "data": {}},
            )
        assert resp.status_code == 409
        assert resp.json()["detail"] == "Cannot send events to a finished run"
    finally:
        _clear_overrides()


@pytest.mark.asyncio
async def test_event_to_completed_run_returns_409(db: AsyncSession) -> None:
    _override_groq(_make_groq_mock())
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            _, run_id = await _make_supervisor_and_run(client, "ORD-EVT-5")
            from app.services.run_service import get_run
            run = await get_run(db, uuid.UUID(run_id))
            run.status = "completed"
            await db.commit()

            resp = await client.post(
                f"/api/runs/{run_id}/events",
                json={"event_type": "order_created", "data": {}},
            )
        assert resp.status_code == 409
        assert resp.json()["detail"] == "Cannot send events to a finished run"
    finally:
        _clear_overrides()


@pytest.mark.asyncio
async def test_invalid_event_type_returns_422() -> None:
    _override_groq(_make_groq_mock())
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                f"/api/runs/{uuid.uuid4()}/events",
                json={"event_type": "totally_made_up", "data": {}},
            )
        assert resp.status_code == 422
    finally:
        _clear_overrides()


@pytest.mark.asyncio
async def test_event_appended_to_events_since_last_wake(db: AsyncSession) -> None:
    _override_groq(_make_groq_mock("no_wake", "just informational"))
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            _, run_id = await _make_supervisor_and_run(client, "ORD-EVT-7")
            await client.post(
                f"/api/runs/{run_id}/events",
                json={"event_type": "shipment_created", "data": {"carrier": "DHL"}},
            )
            run_resp = await client.get(f"/api/runs/{run_id}")
        state = run_resp.json()["state"]
        events = state["events_since_last_wake"]
        assert len(events) == 1
        assert events[0]["event_type"] == "shipment_created"
        assert events[0]["data"]["carrier"] == "DHL"
        assert "received_at" in events[0]
    finally:
        _clear_overrides()


@pytest.mark.asyncio
async def test_activity_log_has_event_received_and_wake_decision(db: AsyncSession) -> None:
    _override_groq(_make_groq_mock("wake", "payment confirmed"))
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            _, run_id = await _make_supervisor_and_run(client, "ORD-EVT-8")
            await client.post(
                f"/api/runs/{run_id}/events",
                json={"event_type": "payment_confirmed", "data": {}},
            )
            activities_resp = await client.get(f"/api/runs/{run_id}/activities")
        types = [a["activity_type"] for a in activities_resp.json()]
        assert "event_received" in types
        assert "wake_decision" in types
    finally:
        _clear_overrides()


@pytest.mark.asyncio
async def test_wake_decision_activity_has_classifier_layer(db: AsyncSession) -> None:
    _override_groq(_make_groq_mock("wake", "needs action"))
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            _, run_id = await _make_supervisor_and_run(client, "ORD-EVT-9")
            await client.post(
                f"/api/runs/{run_id}/events",
                json={"event_type": "payment_failed", "data": {}},
            )
            activities_resp = await client.get(f"/api/runs/{run_id}/activities")
        wake_activities = [
            a for a in activities_resp.json() if a["activity_type"] == "wake_decision"
        ]
        assert len(wake_activities) == 1
        assert "classifier_layer" in wake_activities[0]["payload"]
        assert wake_activities[0]["payload"]["classifier_layer"] == "rules"
    finally:
        _clear_overrides()


@pytest.mark.asyncio
async def test_order_created_full_flow(db: AsyncSession) -> None:
    mock_groq = _make_groq_mock("wake", "new order needs initial processing")
    _override_groq(mock_groq)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            _, run_id = await _make_supervisor_and_run(client, "ORD-EVT-10")
            resp = await client.post(
                f"/api/runs/{run_id}/events",
                json={"event_type": "order_created", "data": {"customer_id": "C-123"}},
            )
            assert resp.status_code == 201
            data = resp.json()
            assert data["event_type"] == "order_created"
            assert data["wake_decision"] is True
            assert data["wake_reason"] == "new order needs initial processing"
            assert uuid.UUID(data["activity_id"])
            assert uuid.UUID(data["run_id"]) == uuid.UUID(run_id)

            activities_resp = await client.get(f"/api/runs/{run_id}/activities")
            activities = activities_resp.json()
            # system_event (run_started) + event_received + wake_decision = 3
            assert len(activities) == 3
            assert activities[0]["activity_type"] == "system_event"
            assert activities[1]["activity_type"] == "event_received"
            assert activities[2]["activity_type"] == "wake_decision"
            assert activities[2]["payload"]["classifier_layer"] == "llm"

            run_resp = await client.get(f"/api/runs/{run_id}")
            state = run_resp.json()["state"]
            assert len(state["events_since_last_wake"]) == 1
            assert state["events_since_last_wake"][0]["event_type"] == "order_created"
    finally:
        _clear_overrides()
