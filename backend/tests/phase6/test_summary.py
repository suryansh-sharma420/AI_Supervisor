"""Unit + integration tests for the summary service."""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.run import RunCreate
from app.schemas.supervisor import SupervisorCreate
from app.services.run_service import create_activity, create_run, get_activities, get_run
from app.services.summary_service import complete_run, generate_final_summary
from app.services.supervisor_service import create_supervisor


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _groq_mock(text: str) -> MagicMock:
    message = MagicMock()
    message.content = text
    choice = MagicMock()
    choice.message = message
    resp = MagicMock()
    resp.choices = [choice]
    groq = MagicMock()
    groq.chat = MagicMock()
    groq.chat.completions = MagicMock()
    groq.chat.completions.create = AsyncMock(return_value=resp)
    return groq


def _groq_error_mock() -> MagicMock:
    groq = MagicMock()
    groq.chat = MagicMock()
    groq.chat.completions = MagicMock()
    groq.chat.completions.create = AsyncMock(side_effect=Exception("Groq unavailable"))
    return groq


async def _make_run(db: AsyncSession, order_id: str) -> tuple:
    sup = await create_supervisor(
        db,
        SupervisorCreate(name=f"Sum Sup {order_id}", base_instruction="Summarise.", available_actions=[]),
    )
    run = await create_run(db, RunCreate(supervisor_id=sup.id, order_id=order_id))
    return sup, run


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_generate_final_summary_returns_structured_text(db: AsyncSession) -> None:
    sup, run = await _make_run(db, "ORD-SUM-1")
    run.completed_at = datetime.now(timezone.utc)

    summary_text = (
        "1. SUMMARY: The order was delivered successfully.\n"
        "2. ACTIONS TAKEN:\n- Notified customer\n"
        "3. KEY LEARNINGS: Communication was timely.\n"
        "4. RECOMMENDATIONS: Continue current process."
    )
    groq = _groq_mock(summary_text)

    result = await generate_final_summary(run, sup, db, groq, completion_reason="terminal_event:delivered")

    assert "SUMMARY" in result
    assert "ACTIONS TAKEN" in result
    assert "KEY LEARNINGS" in result
    assert "RECOMMENDATIONS" in result


@pytest.mark.asyncio
async def test_generate_final_summary_fallback_on_groq_error(db: AsyncSession) -> None:
    sup, run = await _make_run(db, "ORD-SUM-2")
    run.completed_at = datetime.now(timezone.utc)
    groq = _groq_error_mock()

    result = await generate_final_summary(run, sup, db, groq, completion_reason="test")

    assert "Run completed" in result
    assert "Summary generation failed" in result
    assert run.order_id in result


@pytest.mark.asyncio
async def test_complete_run_sets_status_and_completed_at(db: AsyncSession) -> None:
    _, run = await _make_run(db, "ORD-SUM-3")
    groq = _groq_mock("1. SUMMARY: done. 2. ACTIONS TAKEN: none. 3. KEY LEARNINGS: ok. 4. RECOMMENDATIONS: ok.")

    updated = await complete_run(run, db, groq, reason="terminal_event:delivered", final_status="completed")

    assert updated.status == "completed"
    assert updated.completed_at is not None


@pytest.mark.asyncio
async def test_complete_run_creates_final_output_activity(db: AsyncSession) -> None:
    _, run = await _make_run(db, "ORD-SUM-4")
    groq = _groq_mock("Summary text here.")

    await complete_run(run, db, groq, reason="manual_termination", final_status="terminated")

    activities = await get_activities(db, run.id)
    final = [a for a in activities if a.activity_type == "final_output"]
    assert len(final) == 1


@pytest.mark.asyncio
async def test_complete_run_terminated_status(db: AsyncSession) -> None:
    _, run = await _make_run(db, "ORD-SUM-5")
    groq = _groq_mock("Summary.")

    updated = await complete_run(run, db, groq, reason="max_run_age_exceeded", final_status="terminated")

    assert updated.status == "terminated"
    assert updated.final_summary is not None


@pytest.mark.asyncio
async def test_final_output_payload_contains_completion_reason(db: AsyncSession) -> None:
    _, run = await _make_run(db, "ORD-SUM-6")
    groq = _groq_mock("Summary.")

    await complete_run(run, db, groq, reason="terminal_event:refund_requested", final_status="completed")

    activities = await get_activities(db, run.id)
    final = [a for a in activities if a.activity_type == "final_output"]
    assert final[0].payload["completion_reason"] == "terminal_event:refund_requested"
    assert final[0].payload["final_status"] == "completed"
