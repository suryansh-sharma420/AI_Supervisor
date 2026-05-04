"""
Builds LLM prompts for the agent cycle.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.run import Run


def build_system_prompt(supervisor_base_instruction: str, default_sleep_minutes: int) -> str:
    return f"""You are an AI order supervisor agent for an e-commerce order management system.

Your primary instruction from the supervisor configuration:
{supervisor_base_instruction}

Your responsibilities:
- Review the current order state and recent events
- Take appropriate actions using the available tools
- Contact the right team (fulfillment, payments, logistics) when issues arise
- Keep the customer informed when directly relevant
- Create internal notes to document your reasoning
- Update the order state to reflect your assessment
- END every cycle by calling sleep()

Sleep Configuration:
- The default sleep duration for this supervisor is {default_sleep_minutes} minutes.
- You should use this duration unless you have a strong reason to check back sooner (e.g., waiting for a high-priority update) or later.

Rules:
- Always include reasoning in every tool call so humans can audit your decisions
- Use update_state to record your current assessment of the order situation
- You MUST call sleep() to end every cycle — do not leave a cycle open
- Do not call tools after sleep(); it is always the last action
- Do not loop excessively; take the minimal set of actions needed
- If you are unsure, create an internal note and sleep rather than escalating unnecessarily
"""


def build_user_prompt(run: "Run", events_since_last_wake: list) -> str:
    state = run.state
    order_id = state.get("order_id", run.order_id)
    order_status = state.get("order_status", "unknown")
    iteration_count = state.get("iteration_count", 0)
    agent_summary = state.get("agent_summary", "No prior summary.")
    custom_instructions = state.get("custom_instructions", [])

    lines: list[str] = [
        f"ORDER ID: {order_id}",
        f"ORDER STATUS: {order_status}",
        f"ITERATION: {iteration_count}",
        "",
        "PRIOR AGENT SUMMARY:",
        agent_summary,
    ]

    if custom_instructions:
        lines += ["", "CUSTOM INSTRUCTIONS (follow these carefully):"]
        for i, instr in enumerate(custom_instructions, 1):
            lines.append(f"  {i}. {instr}")

    if events_since_last_wake:
        lines += ["", f"RECENT EVENTS ({len(events_since_last_wake)} since last wake):"]
        for evt in events_since_last_wake[-10:]:
            event_type = evt.get("event_type", "unknown")
            data = evt.get("data", {})
            received_at = evt.get("received_at", "")
            data_str = json.dumps(data) if data else "{}"
            lines.append(f"  - [{received_at[:19]}] {event_type}: {data_str}")
    else:
        lines += ["", "RECENT EVENTS: none since last wake"]

    lines += [
        "",
        "INSTRUCTIONS:",
        "Review the above and take any necessary actions.",
        "Use update_state to record your assessment.",
        "When finished, call sleep() with a duration and reason.",
    ]

    return "\n".join(lines)


def compact_events(
    events: list, max_recent: int = 8
) -> tuple[list, str | None]:
    """
    If events exceed max_recent, compact the older ones into a summary string.
    Returns (recent_events, compact_summary_or_None).
    """
    if len(events) <= max_recent:
        return events, None

    old_events = events[:-max_recent]
    recent_events = events[-max_recent:]

    parts: list[str] = []
    for evt in old_events:
        event_type = evt.get("event_type", "unknown")
        received_at = evt.get("received_at", "")
        time_str = received_at[11:16] if len(received_at) >= 16 else received_at
        parts.append(f"{event_type} at {time_str}")

    compact_summary = "Earlier: " + ", ".join(parts)
    return recent_events, compact_summary
