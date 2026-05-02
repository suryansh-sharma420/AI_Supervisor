"""API tests for the manual wake endpoint."""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_groq_client
from app.main import app
from app.services.run_service import get_activities, get_run


def _summary_groq_mock() -> MagicMock:
    groq = MagicMock()
    groq.chat = MagicMock()
    groq.chat.completions = MagicMock()
    groq.chat.completions.create = AsyncMock(return_value=_build_resp("Summary."))
    return groq


def _build_resp(content: str) -> MagicMock:
    message = MagicMock()
    message.content = content
    choice = MagicMock()
    choice.message = message
    resp = MagicMock()
    resp.choices = [choice]
    return resp


def _override_groq(mock: MagicMock) -> None:
    app.dependency_overrides[get_groq_client] = lambda: mock


def _clear_overrides() -> None:
    app.dependency_overrides.pop(get_groq_client, None)


async def _create_run(client: AsyncClient, order_id: str) -> str:
    sup_resp = await client.post(
        "/api/supervisors",
        json={"name": f"Wake Sup {order_id}", "base_instruction": "Wake test."},
    )
    sup_id = sup_resp.json()["id"]
    run_resp = await client.post(
        "/api/runs",
        json={"supervisor_id": sup_id, "order_id": order_id},
    )
    return run_resp.json()["id"]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_wake_sleeping_run_becomes_active(db: AsyncSession) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        run_id = await _create_run(client, "ORD-WAKE-1")
        # Set to sleeping via DB
        run = await get_run(db, uuid.UUID(run_id))
        run.status = "sleeping"
        run.wake_at = datetime.now(timezone.utc) + timedelta(hours=1)
        await db.commit()

        resp = await client.post(f"/api/runs/{run_id}/wake")

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "active"


@pytest.mark.asyncio
async def test_wake_creates_manual_wake_activity(db: AsyncSession) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        run_id = await _create_run(client, "ORD-WAKE-2")
        run = await get_run(db, uuid.UUID(run_id))
        run.status = "sleeping"
        await db.commit()

        await client.post(f"/api/runs/{run_id}/wake")

    activities = await get_activities(db, uuid.UUID(run_id))
    wake_events = [
        a for a in activities
        if a.activity_type == "system_event" and a.payload.get("event") == "manual_wake"
    ]
    assert len(wake_events) == 1
    assert wake_events[0].payload["reason"] == "user triggered manual wake"


@pytest.mark.asyncio
async def test_wake_active_run_returns_409() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        run_id = await _create_run(client, "ORD-WAKE-3")
        resp = await client.post(f"/api/runs/{run_id}/wake")

    assert resp.status_code == 409
    assert "not sleeping" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_wake_paused_run_returns_409(db: AsyncSession) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        run_id = await _create_run(client, "ORD-WAKE-4")
        await client.post(f"/api/runs/{run_id}/interrupt")
        resp = await client.post(f"/api/runs/{run_id}/wake")

    assert resp.status_code == 409
    assert "not sleeping" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_wake_terminated_run_returns_409(db: AsyncSession) -> None:
    _override_groq(_summary_groq_mock())
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            run_id = await _create_run(client, "ORD-WAKE-5")
            await client.post(f"/api/runs/{run_id}/terminate")
            resp = await client.post(f"/api/runs/{run_id}/wake")
        assert resp.status_code == 409
    finally:
        _clear_overrides()


@pytest.mark.asyncio
async def test_wake_nonexistent_run_returns_404() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(f"/api/runs/{uuid.uuid4()}/wake")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_wake_clears_wake_at(db: AsyncSession) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        run_id = await _create_run(client, "ORD-WAKE-7")
        run = await get_run(db, uuid.UUID(run_id))
        run.status = "sleeping"
        run.wake_at = datetime.now(timezone.utc) + timedelta(hours=2)
        await db.commit()

        resp = await client.post(f"/api/runs/{run_id}/wake")

    assert resp.status_code == 200
    await db.refresh(run)
    assert run.wake_at is None
