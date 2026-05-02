from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.classifier import (
    CRITICAL_EVENTS,
    NON_URGENT_EVENTS,
    classify_event,
)


def _mock_groq(decision: str, reason: str) -> MagicMock:
    """Build a mock AsyncGroq client that returns the given decision JSON."""
    import json

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


@pytest.mark.asyncio
@pytest.mark.parametrize("event_type", sorted(CRITICAL_EVENTS))
async def test_critical_events_always_wake(event_type: str) -> None:
    groq = _mock_groq("no_wake", "should not be called")
    should_wake, reason, layer = await classify_event(
        event_type=event_type,
        event_data={},
        order_status="active",
        wake_aggressiveness="conservative",
        groq_client=groq,
    )
    assert should_wake is True
    assert layer == "rules"
    groq.chat.completions.create.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("event_type", sorted(NON_URGENT_EVENTS))
async def test_non_urgent_events_never_wake(event_type: str) -> None:
    groq = _mock_groq("wake", "should not be called")
    should_wake, reason, layer = await classify_event(
        event_type=event_type,
        event_data={},
        order_status="active",
        wake_aggressiveness="aggressive",
        groq_client=groq,
    )
    assert should_wake is False
    assert layer == "rules"
    groq.chat.completions.create.assert_not_called()


@pytest.mark.asyncio
async def test_unclear_event_normal_aggressiveness_wake() -> None:
    groq = _mock_groq("wake", "customer message may require response")
    should_wake, reason, layer = await classify_event(
        event_type="customer_message_received",
        event_data={"message": "Where is my order?"},
        order_status="shipped",
        wake_aggressiveness="normal",
        groq_client=groq,
    )
    assert should_wake is True
    assert reason == "customer message may require response"
    assert layer == "llm"
    groq.chat.completions.create.assert_called_once()


@pytest.mark.asyncio
async def test_unclear_event_conservative_no_wake() -> None:
    groq = _mock_groq("no_wake", "shipment delay is minor, can wait")
    should_wake, reason, layer = await classify_event(
        event_type="shipment_delayed",
        event_data={"delay_hours": 2},
        order_status="shipped",
        wake_aggressiveness="conservative",
        groq_client=groq,
    )
    assert should_wake is False
    assert reason == "shipment delay is minor, can wait"
    assert layer == "llm"


@pytest.mark.asyncio
async def test_malformed_json_defaults_to_wake() -> None:
    message = MagicMock()
    message.content = "not valid json at all"
    choice = MagicMock()
    choice.message = message
    completion = MagicMock()
    completion.choices = [choice]
    groq = MagicMock()
    groq.chat = MagicMock()
    groq.chat.completions = MagicMock()
    groq.chat.completions.create = AsyncMock(return_value=completion)

    should_wake, reason, layer = await classify_event(
        event_type="order_created",
        event_data={},
        order_status="created",
        wake_aggressiveness="normal",
        groq_client=groq,
    )
    assert should_wake is True
    assert "classifier error" in reason
    assert layer == "llm"


@pytest.mark.asyncio
async def test_rules_layer_classifier_layer_field() -> None:
    groq = _mock_groq("wake", "irrelevant")
    _, _, layer = await classify_event(
        event_type="payment_failed",
        event_data={},
        order_status="created",
        wake_aggressiveness="normal",
        groq_client=groq,
    )
    assert layer == "rules"


@pytest.mark.asyncio
async def test_llm_layer_classifier_layer_field() -> None:
    groq = _mock_groq("wake", "order just created, agent should review")
    _, _, layer = await classify_event(
        event_type="order_created",
        event_data={},
        order_status="created",
        wake_aggressiveness="normal",
        groq_client=groq,
    )
    assert layer == "llm"
