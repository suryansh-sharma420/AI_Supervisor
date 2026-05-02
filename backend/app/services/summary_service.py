import logging
import uuid
from datetime import datetime, timezone

from groq import AsyncGroq
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.services.run_service import create_activity, get_activities
from app.services.supervisor_service import get_supervisor

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are summarizing a completed order supervision run. "
    "Be concise and structured."
)

_USER_PROMPT_TEMPLATE = """\
Order ID: {order_id}
Run duration: {duration}
Completion reason: {completion_reason}

Events received: {event_list}

Actions taken by agent: {action_list}

Final order status: {order_status}

Generate a final summary with these sections:
1. SUMMARY: What happened with this order (2-3 sentences)
2. ACTIONS TAKEN: Bullet list of key actions
3. KEY LEARNINGS: What went well or could be improved
4. RECOMMENDATIONS: Suggestions for similar future orders"""


async def generate_final_summary(
    run,
    supervisor,
    db: AsyncSession,
    groq_client: AsyncGroq,
    completion_reason: str = "unknown",
) -> str:
    activities = await get_activities(db, run.id)

    event_types = [
        a.payload.get("event_type", "unknown")
        for a in activities
        if a.activity_type == "event_received"
    ]
    actions = [
        f"{a.payload.get('action', 'unknown')}: {a.payload.get('reasoning', '')}"
        for a in activities
        if a.activity_type == "agent_action"
    ]

    completed_at = run.completed_at or datetime.now(timezone.utc)
    duration_seconds = (completed_at - run.started_at).total_seconds()
    hours, remainder = divmod(int(duration_seconds), 3600)
    minutes = remainder // 60
    duration_str = f"{hours}h {minutes}m"

    order_status = run.state.get("order_status", "unknown")
    order_id = run.order_id

    event_list = ", ".join(event_types) if event_types else "none"
    action_list = "\n".join(f"- {a}" for a in actions) if actions else "none"

    user_prompt = _USER_PROMPT_TEMPLATE.format(
        order_id=order_id,
        duration=duration_str,
        completion_reason=completion_reason,
        event_list=event_list,
        action_list=action_list,
        order_status=order_status,
    )

    try:
        response = await groq_client.chat.completions.create(
            model=settings.GROQ_AGENT_MODEL,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            max_tokens=512,
        )
        return response.choices[0].message.content or ""
    except Exception as exc:
        logger.warning("Summary generation failed for run %s: %s", run.id, exc)
        return (
            f"Run completed. Summary generation failed. "
            f"Order: {order_id}, Duration: {duration_str}, "
            f"Actions taken: {len(actions)}"
        )


async def complete_run(
    run,
    db: AsyncSession,
    groq_client: AsyncGroq,
    reason: str,
    final_status: str = "completed",
) -> object:
    supervisor = await get_supervisor(db, run.supervisor_id)

    run.status = final_status
    run.completed_at = datetime.now(timezone.utc)

    summary = await generate_final_summary(
        run, supervisor, db, groq_client, completion_reason=reason
    )
    run.final_summary = summary

    await create_activity(
        db,
        run.id,
        "final_output",
        {
            "completion_reason": reason,
            "final_status": final_status,
            "summary": summary,
        },
    )

    await db.commit()
    await db.refresh(run)
    return run
