import json
import logging

from groq import AsyncGroq

from app.config import settings

logger = logging.getLogger(__name__)

CRITICAL_EVENTS = {"payment_failed", "delivered", "refund_requested"}
NON_URGENT_EVENTS = {"no_update_for_n_hours", "shipment_created"}
# Everything else is UNCLEAR and goes to the LLM layer
# order_created, payment_confirmed, shipment_delayed, customer_message_received

_SYSTEM_PROMPT = (
    "You are a classifier for an order management system. "
    "Your job is to decide if an incoming event requires "
    "immediate agent attention or can wait until the next "
    "scheduled check. Reply with JSON only: "
    '{"decision": "wake" or "no_wake", "reason": "one sentence"}'
)

_USER_PROMPT_TEMPLATE = """\
Event type: {event_type}
Event data: {event_data}
Order status: {order_status}
Wake aggressiveness: {wake_aggressiveness}

conservative = only wake for truly urgent issues
normal = wake for anything that might need action soon
aggressive = wake for almost everything, err on side of action"""


async def classify_event(
    event_type: str,
    event_data: dict,
    order_status: str,
    wake_aggressiveness: str,
    groq_client: AsyncGroq,
) -> tuple[bool, str, str]:
    """
    Returns (should_wake, reason, classifier_layer).
    classifier_layer is "rules" or "llm".
    """
    if event_type in CRITICAL_EVENTS:
        return True, f"{event_type} is a critical event requiring immediate attention", "rules"

    if event_type in NON_URGENT_EVENTS:
        return False, f"{event_type} is informational; agent will see it on next scheduled wake", "rules"

    # UNCLEAR — call LLM
    user_prompt = _USER_PROMPT_TEMPLATE.format(
        event_type=event_type,
        event_data=json.dumps(event_data),
        order_status=order_status,
        wake_aggressiveness=wake_aggressiveness,
    )

    try:
        response = await groq_client.chat.completions.create(
            model=settings.GROQ_CLASSIFIER_MODEL,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0,
            max_tokens=128,
        )
        raw = response.choices[0].message.content or ""
        parsed = json.loads(raw)
        decision = parsed["decision"]
        reason = parsed["reason"]
        should_wake = decision == "wake"
        return should_wake, reason, "llm"
    except Exception as exc:
        logger.warning("Classifier LLM call failed: %s", exc)
        return True, "classifier error, defaulting to wake for safety", "llm"
