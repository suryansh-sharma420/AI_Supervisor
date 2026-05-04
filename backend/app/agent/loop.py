"""
Core agent execution loop.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timedelta, timezone

from groq import AsyncGroq
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.context import build_system_prompt, build_user_prompt, compact_events
from app.agent.tools import BUSINESS_ACTION_TOOLS, get_tools_for_supervisor
from app.config import settings
from app.services.run_service import create_activity, get_run
from app.services.supervisor_service import get_supervisor

logger = logging.getLogger(__name__)

_MAX_ITERATIONS = 10
_DEFAULT_SLEEP_MINUTES = 60
_DEFAULT_SLEEP_ERROR_MINUTES = 30


async def execute_agent_cycle(
    run_id: uuid.UUID,
    db: AsyncSession,
    groq_client: AsyncGroq,
) -> dict:
    summary: dict = {
        "actions_taken": [],
        "slept": False,
        "sleep_duration_minutes": None,
        "iterations": 0,
        "terminated_early": False,
    }

    run = await get_run(db, run_id)
    if run is None:
        summary["terminated_early"] = True
        return summary

    supervisor = await get_supervisor(db, run.supervisor_id)

    if run.status not in {"active", "running"}:
        summary["terminated_early"] = True
        return summary

    # Mark as running and increment iteration count
    run.status = "running"
    iteration_count = int(run.state.get("iteration_count", 0)) + 1
    run.state = {**run.state, "iteration_count": iteration_count}
    await db.commit()
    await db.refresh(run)

    # Compact events if needed
    events = list(run.state.get("events_since_last_wake", []))
    recent_events, compact_summary = compact_events(events)
    if compact_summary is not None:
        prior_summary = run.state.get("agent_summary", "")
        new_summary = f"{compact_summary}\n\n{prior_summary}".strip()
        run.state = {**run.state, "agent_summary": new_summary, "events_since_last_wake": recent_events}
        await db.commit()
        await db.refresh(run)

    # Build prompts
    dynamic_sleep = supervisor.default_sleep_minutes if supervisor else _DEFAULT_SLEEP_MINUTES
    system_prompt = build_system_prompt(
        supervisor.base_instruction if supervisor else "Supervise orders carefully.",
        dynamic_sleep
    )
    user_prompt = build_user_prompt(run, run.state.get("events_since_last_wake", []))

    # Choose model
    llm_settings = supervisor.llm_settings if supervisor and supervisor.llm_settings else {}
    model = llm_settings.get("model", settings.GROQ_AGENT_MODEL)

    tools = get_tools_for_supervisor(
        supervisor.available_actions if supervisor else [],
        dynamic_sleep
    )

    messages: list[dict] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    tool_choice: str = "required"

    try:
        for iteration in range(_MAX_ITERATIONS):
            summary["iterations"] += 1

            response = await groq_client.chat.completions.create(
                model=model,
                messages=messages,
                tools=tools,
                tool_choice=tool_choice,
            )

            assistant_message = response.choices[0].message
            tool_calls = assistant_message.tool_calls or []

            if not tool_calls:
                break

            # Build tool results for the next message turn
            tool_results: list[dict] = []
            slept = False

            for tc in tool_calls:
                tool_name = tc.function.name
                try:
                    tool_args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    tool_args = {}

                if tool_name in BUSINESS_ACTION_TOOLS:
                    await create_activity(
                        db,
                        run_id,
                        "agent_action",
                        {
                            "action": tool_name,
                            "parameters": tool_args,
                            "reasoning": tool_args.get("reasoning", ""),
                        },
                    )
                    summary["actions_taken"].append(tool_name)
                    tool_results.append(
                        {"tool_call_id": tc.id, "role": "tool", "content": "Action recorded."}
                    )

                elif tool_name == "update_state":
                    key = tool_args.get("key", "")
                    value = tool_args.get("value", "")
                    run.state = {**run.state, key: value}
                    await create_activity(
                        db,
                        run_id,
                        "agent_action",
                        {
                            "action": "update_state",
                            "key": key,
                            "value": value,
                            "reasoning": tool_args.get("reasoning", ""),
                        },
                    )
                    summary["actions_taken"].append("update_state")
                    tool_results.append(
                        {"tool_call_id": tc.id, "role": "tool", "content": "State updated."}
                    )

                elif tool_name == "sleep":
                    duration_minutes = int(tool_args.get("duration_minutes", dynamic_sleep))
                    reason = tool_args.get("reason", "")
                    next_check_focus = tool_args.get("next_check_focus", "")

                    wake_at = datetime.now(timezone.utc) + timedelta(minutes=duration_minutes)
                    run.status = "sleeping"
                    run.wake_at = wake_at
                    run.state = {
                        **run.state,
                        "agent_summary": reason,
                        "next_check_focus": next_check_focus,
                        "events_since_last_wake": [],
                    }

                    await create_activity(
                        db,
                        run_id,
                        "sleep_decision",
                        {
                            "duration_minutes": duration_minutes,
                            "reason": reason,
                            "next_check_focus": next_check_focus,
                            "wake_at": wake_at.isoformat(),
                        },
                    )

                    await db.commit()
                    summary["slept"] = True
                    summary["sleep_duration_minutes"] = duration_minutes
                    return summary

            # Append assistant turn and tool results for next LLM call
            messages.append(
                {
                    "role": "assistant",
                    "content": assistant_message.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                        }
                        for tc in tool_calls
                    ],
                }
            )
            messages.extend(tool_results)
            tool_choice = "auto"

    except Exception as exc:
        logger.exception("Agent cycle error for run %s: %s", run_id, exc)
        await create_activity(
            db,
            run_id,
            "system_event",
            {"event": "agent_error", "error": str(exc)},
        )
        wake_at = datetime.now(timezone.utc) + timedelta(minutes=_DEFAULT_SLEEP_ERROR_MINUTES)
        run.status = "sleeping"
        run.wake_at = wake_at
        run.state = {
            **run.state,
            "events_since_last_wake": [],
        }
        await db.commit()
        summary["slept"] = True
        summary["sleep_duration_minutes"] = _DEFAULT_SLEEP_ERROR_MINUTES
        summary["terminated_early"] = True
        return summary

    # Loop exited without sleep — apply default sleep from supervisor
    dynamic_default = supervisor.default_sleep_minutes if supervisor else _DEFAULT_SLEEP_MINUTES
    logger.warning("Agent for run %s did not call sleep(); applying default %d-minute sleep", run_id, dynamic_default)
    wake_at = datetime.now(timezone.utc) + timedelta(minutes=dynamic_default)
    run.status = "sleeping"
    run.wake_at = wake_at
    run.state = {**run.state, "events_since_last_wake": []}
    await create_activity(
        db,
        run_id,
        "sleep_decision",
        {
            "duration_minutes": dynamic_default,
            "reason": f"agent did not call sleep, defaulting to {dynamic_default} minute sleep from supervisor config",
            "next_check_focus": "",
            "wake_at": wake_at.isoformat(),
        },
    )
    await db.commit()
    summary["slept"] = True
    summary["sleep_duration_minutes"] = dynamic_default
    return summary
