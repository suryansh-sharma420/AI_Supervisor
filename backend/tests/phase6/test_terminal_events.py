"""Integration tests for terminal event detection."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_groq_client
from app.main import app
from app.services.run_service import get_activities, get_run


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_groq_mock(
    classifier_decision: str = "wake",
    classifier_reason: str = "test",
    summary_text: str = "1. SUMMARY: done. 2. ACTIONS TAKEN: none. 3. KEY LEARNINGS: ok. 4. RECOMMENDATIONS: ok.",
) -> MagicMock:
    """
    Mock that handles both classifier JSON responses and summary text responses.
    First call returns classifier JSON, subsequent calls return summary text.
    """
    import json

    classifier_resp = _build_resp(json.dumps({"decision": classifier_decision, "reason": classifier_reason}))
    summary_resp = _build_resp(summary_text)

    groq = MagicMock()
    groq.chat = MagicMock()
    groq.chat.completions = MagicMock()
    # Use side_effect list: classifier first, then summary (for terminal events only summary is called)
    groq.chat.completions.create = AsyncMock(side_effect=[classifier_resp, summary_resp, summary_resp])
    return groq


def _make_summary_only_mock(summary_text: str = "1. SUMMARY: done. 2. ACTIONS TAKEN: -. 3. KEY LEARNINGS: ok. 4. RECOMMENDATIONS: ok.") -> MagicMock:
    """Mock that returns summary text — for terminal events which skip classifier."""
    groq = MagicMock()
    groq.chat = MagicMock()
    groq.chat.completions = MagicMock()
    groq.chat.completions.create = AsyncMock(return_value=_build_resp(summary_text))
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


async def _make_supervisor_and_run(client: AsyncClient, order_id: str, status: str = "active") -> tuple[str, str]:
    sup_resp = await client.post(
        "/api/supervisors",
        json={"name": f"Term Sup {order_id}", "base_instruction": "Handle terminal events."},
    )
    sup_id = sup_resp.json()["id"]
    run_resp = await client.post(
        "/api/runs",
        json={"supervisor_id": sup_id, "order_id": order_id},
    )
    run_id = run_resp.json()["id"]
    return sup_id, run_id


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_delivered_event_completes_run(db: AsyncSession) -> None:
    _override_groq(_make_summary_only_mock())
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            _, run_id = await _make_supervisor_and_run(client, "ORD-TERM-1")
            resp = await client.post(
                f"/api/runs/{run_id}/events",
                json={"event_type": "delivered", "data": {}},
            )
        assert resp.status_code == 201
        assert resp.json()["wake_decision"] is True
        assert resp.json()["wake_reason"] == "terminal event, run completed"

        run = await get_run(db, uuid.UUID(run_id))
        assert run.status == "completed"
        assert run.completed_at is not None
        assert run.final_summary is not None

        activities = await get_activities(db, uuid.UUID(run_id))
        assert any(a.activity_type == "final_output" for a in activities)
    finally:
        _clear_overrides()


@pytest.mark.asyncio
async def test_refund_requested_event_completes_run(db: AsyncSession) -> None:
    _override_groq(_make_summary_only_mock())
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            _, run_id = await _make_supervisor_and_run(client, "ORD-TERM-2")
            resp = await client.post(
                f"/api/runs/{run_id}/events",
                json={"event_type": "refund_requested", "data": {"reason": "damaged"}},
            )
        assert resp.status_code == 201
        run = await get_run(db, uuid.UUID(run_id))
        assert run.status == "completed"
        assert run.completed_at is not None
        assert run.final_summary is not None
    finally:
        _clear_overrides()


@pytest.mark.asyncio
async def test_delivered_event_on_sleeping_run_completes(db: AsyncSession) -> None:
    _override_groq(_make_summary_only_mock())
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            _, run_id = await _make_supervisor_and_run(client, "ORD-TERM-3")
            # Put run to sleep
            run = await get_run(db, uuid.UUID(run_id))
            run.status = "sleeping"
            await db.commit()

            resp = await client.post(
                f"/api/runs/{run_id}/events",
                json={"event_type": "delivered", "data": {}},
            )
        assert resp.status_code == 201
        await db.refresh(run)
        # Should be completed, not sleeping or active
        assert run.status == "completed"
    finally:
        _clear_overrides()


@pytest.mark.asyncio
async def test_non_terminal_event_does_not_complete_run(db: AsyncSession) -> None:
    import json

    classifier_resp = _build_resp(json.dumps({"decision": "wake", "reason": "payment issue"}))
    summary_resp = _build_resp("Summary.")
    groq = MagicMock()
    groq.chat = MagicMock()
    groq.chat.completions = MagicMock()
    groq.chat.completions.create = AsyncMock(side_effect=[classifier_resp, summary_resp])
    _override_groq(groq)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            _, run_id = await _make_supervisor_and_run(client, "ORD-TERM-4")
            resp = await client.post(
                f"/api/runs/{run_id}/events",
                json={"event_type": "payment_failed", "data": {}},
            )
        assert resp.status_code == 201
        run = await get_run(db, uuid.UUID(run_id))
        assert run.status != "completed"

        activities = await get_activities(db, uuid.UUID(run_id))
        assert not any(a.activity_type == "final_output" for a in activities)
    finally:
        _clear_overrides()


@pytest.mark.asyncio
async def test_event_after_terminal_event_returns_409(db: AsyncSession) -> None:
    _override_groq(_make_summary_only_mock())
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            _, run_id = await _make_supervisor_and_run(client, "ORD-TERM-5")
            await client.post(
                f"/api/runs/{run_id}/events",
                json={"event_type": "delivered", "data": {}},
            )
            resp = await client.post(
                f"/api/runs/{run_id}/events",
                json={"event_type": "payment_confirmed", "data": {}},
            )
        assert resp.status_code == 409
        assert resp.json()["detail"] == "Cannot send events to a finished run"
    finally:
        _clear_overrides()


@pytest.mark.asyncio
async def test_terminal_event_generates_final_summary_with_content(db: AsyncSession) -> None:
    summary_text = (
        "1. SUMMARY: Order delivered successfully after 2 days.\n"
        "2. ACTIONS TAKEN:\n- Notified logistics team\n- Messaged customer\n"
        "3. KEY LEARNINGS: Proactive communication helped.\n"
        "4. RECOMMENDATIONS: Maintain current SLAs."
    )
    _override_groq(_make_summary_only_mock(summary_text))
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            _, run_id = await _make_supervisor_and_run(client, "ORD-TERM-6")
            await client.post(
                f"/api/runs/{run_id}/events",
                json={"event_type": "delivered", "data": {}},
            )
        run = await get_run(db, uuid.UUID(run_id))
        assert run.final_summary is not None
        assert "SUMMARY" in run.final_summary
    finally:
        _clear_overrides()
