"""
API tests for the /trigger endpoint.
"""

import json
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_groq_client
from app.main import app
from app.services.run_service import get_activities, get_run


def _tool_call(name: str, args: dict, call_id: str | None = None) -> MagicMock:
    tc = MagicMock()
    tc.id = call_id or f"call_{name}_{uuid.uuid4().hex[:6]}"
    tc.function = MagicMock()
    tc.function.name = name
    tc.function.arguments = json.dumps(args)
    return tc


def _groq_response(tool_calls: list, content: str = "") -> MagicMock:
    message = MagicMock()
    message.content = content
    message.tool_calls = tool_calls or None
    choice = MagicMock()
    choice.message = message
    resp = MagicMock()
    resp.choices = [choice]
    return resp


def _make_groq_mock_sleeping(duration: int = 60) -> MagicMock:
    """Mock that immediately calls sleep()."""
    response = _groq_response([
        _tool_call("sleep", {
            "duration_minutes": duration,
            "reason": "Test sleep",
            "next_check_focus": "nothing",
        }),
    ])
    groq = MagicMock()
    groq.chat = MagicMock()
    groq.chat.completions = MagicMock()
    groq.chat.completions.create = AsyncMock(return_value=response)
    return groq


def _override_groq(mock: MagicMock) -> None:
    app.dependency_overrides[get_groq_client] = lambda: mock


def _clear_overrides() -> None:
    app.dependency_overrides.pop(get_groq_client, None)


async def _create_supervisor_and_run(client: AsyncClient, order_id: str) -> tuple[str, str]:
    sup_resp = await client.post(
        "/api/supervisors",
        json={"name": f"Trigger Sup {order_id}", "base_instruction": "Test supervisor."},
    )
    sup_id = sup_resp.json()["id"]
    run_resp = await client.post(
        "/api/runs",
        json={"supervisor_id": sup_id, "order_id": order_id},
    )
    return sup_id, run_resp.json()["id"]


@pytest.mark.asyncio
async def test_trigger_active_run_returns_200(db: AsyncSession) -> None:
    _override_groq(_make_groq_mock_sleeping())
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            _, run_id = await _create_supervisor_and_run(client, "ORD-TRG-1")
            resp = await client.post(f"/api/runs/{run_id}/trigger")
        assert resp.status_code == 200
        data = resp.json()
        assert data["run_id"] == run_id
        assert "slept" in data
        assert "actions_taken" in data
        assert "iterations" in data
        assert data["slept"] is True
    finally:
        _clear_overrides()


@pytest.mark.asyncio
async def test_trigger_terminated_run_returns_409(db: AsyncSession) -> None:
    _override_groq(_make_groq_mock_sleeping())
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            _, run_id = await _create_supervisor_and_run(client, "ORD-TRG-2")
            await client.post(f"/api/runs/{run_id}/terminate")
            resp = await client.post(f"/api/runs/{run_id}/trigger")
        assert resp.status_code == 409
        assert resp.json()["detail"] == "Run is already finished"
    finally:
        _clear_overrides()


@pytest.mark.asyncio
async def test_trigger_already_running_returns_409(db: AsyncSession) -> None:
    _override_groq(_make_groq_mock_sleeping())
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            _, run_id = await _create_supervisor_and_run(client, "ORD-TRG-3")
            # Manually set status to "running"
            run = await get_run(db, uuid.UUID(run_id))
            run.status = "running"
            await db.commit()
            resp = await client.post(f"/api/runs/{run_id}/trigger")
        assert resp.status_code == 409
        assert resp.json()["detail"] == "Agent is already running for this run"
    finally:
        _clear_overrides()


@pytest.mark.asyncio
async def test_trigger_creates_activity_records(db: AsyncSession) -> None:
    # Mock: call a business action then sleep
    action_response = _groq_response([
        _tool_call("create_internal_note", {
            "note": "Order looks fine", "reasoning": "Reviewing order"
        }),
    ])
    sleep_response = _groq_response([
        _tool_call("sleep", {
            "duration_minutes": 60,
            "reason": "Nothing urgent",
            "next_check_focus": "new events",
        }),
    ])
    groq = MagicMock()
    groq.chat = MagicMock()
    groq.chat.completions = MagicMock()
    groq.chat.completions.create = AsyncMock(side_effect=[action_response, sleep_response])
    _override_groq(groq)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            _, run_id = await _create_supervisor_and_run(client, "ORD-TRG-4")
            await client.post(f"/api/runs/{run_id}/trigger")

        activities = await get_activities(db, uuid.UUID(run_id))
        types = [a.activity_type for a in activities]
        assert "agent_action" in types
        assert "sleep_decision" in types
    finally:
        _clear_overrides()


@pytest.mark.asyncio
async def test_trigger_run_status_sleeping_after_completion(db: AsyncSession) -> None:
    _override_groq(_make_groq_mock_sleeping(90))
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            _, run_id = await _create_supervisor_and_run(client, "ORD-TRG-5")
            resp = await client.post(f"/api/runs/{run_id}/trigger")

        assert resp.status_code == 200
        run = await get_run(db, uuid.UUID(run_id))
        assert run.status == "sleeping"
        assert run.wake_at is not None
        assert run.state["events_since_last_wake"] == []
    finally:
        _clear_overrides()
