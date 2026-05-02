from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from app.agent.context import (
    build_system_prompt,
    build_user_prompt,
    compact_events,
)


def _make_run(
    order_id: str = "ORD-001",
    order_status: str = "active",
    custom_instructions: list | None = None,
    agent_summary: str = "All good.",
    iteration_count: int = 1,
    events: list | None = None,
) -> MagicMock:
    run = MagicMock()
    run.order_id = order_id
    run.state = {
        "order_id": order_id,
        "order_status": order_status,
        "custom_instructions": custom_instructions or [],
        "agent_summary": agent_summary,
        "iteration_count": iteration_count,
        "events_since_last_wake": events or [],
    }
    return run


def test_build_system_prompt_includes_base_instruction() -> None:
    prompt = build_system_prompt("Escalate payment failures immediately.")
    assert "Escalate payment failures immediately." in prompt


def test_build_system_prompt_includes_sleep_instruction() -> None:
    prompt = build_system_prompt("Base instruction.")
    assert "sleep()" in prompt


def test_build_user_prompt_includes_order_id_and_status() -> None:
    run = _make_run(order_id="ORD-XYZ", order_status="shipped")
    prompt = build_user_prompt(run, [])
    assert "ORD-XYZ" in prompt
    assert "shipped" in prompt


def test_build_user_prompt_includes_custom_instructions() -> None:
    run = _make_run(custom_instructions=["Do not refund", "Escalate to manager"])
    prompt = build_user_prompt(run, [])
    assert "Do not refund" in prompt
    assert "Escalate to manager" in prompt


def test_build_user_prompt_includes_agent_summary() -> None:
    run = _make_run(agent_summary="Payment was declined twice.")
    prompt = build_user_prompt(run, [])
    assert "Payment was declined twice." in prompt


def test_compact_events_unchanged_when_under_max() -> None:
    events = [{"event_type": f"event_{i}", "data": {}, "received_at": ""} for i in range(5)]
    result, summary = compact_events(events, max_recent=8)
    assert result == events
    assert summary is None


def test_compact_events_shortened_when_over_max() -> None:
    events = [{"event_type": f"event_{i}", "data": {}, "received_at": ""} for i in range(12)]
    result, summary = compact_events(events, max_recent=8)
    assert len(result) == 8
    assert summary is not None


def test_compact_events_returns_non_none_summary_on_compaction() -> None:
    events = [{"event_type": "payment_failed", "data": {}, "received_at": "2026-05-01T14:00:00Z"}
              for _ in range(10)]
    _, summary = compact_events(events, max_recent=8)
    assert summary is not None
    assert isinstance(summary, str)
    assert len(summary) > 0


def test_compact_events_summary_contains_old_event_types() -> None:
    events = (
        [{"event_type": "payment_failed", "data": {}, "received_at": "2026-05-01T14:00:00Z"}] * 3
        + [{"event_type": "shipment_created", "data": {}, "received_at": "2026-05-01T15:00:00Z"}] * 9
    )
    _, summary = compact_events(events, max_recent=8)
    assert summary is not None
    assert "payment_failed" in summary
