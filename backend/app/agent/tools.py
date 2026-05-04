"""
Groq-compatible tool definitions for the order supervisor agent.
"""
import json
import uuid

BUSINESS_ACTION_TOOLS = [
    "message_fulfillment_team",
    "message_payments_team",
    "message_logistics_team",
    "message_customer",
    "create_internal_note",
]

_MESSAGE_PARAMS = {
    "type": "object",
    "properties": {
        "message": {
            "type": "string",
            "description": "The message to send.",
        },
        "reasoning": {
            "type": "string",
            "description": "Why you are sending this message.",
        },
    },
    "required": ["message", "reasoning"],
}

AVAILABLE_TOOLS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "message_fulfillment_team",
            "description": (
                "Send a message to the fulfillment team about order picking, "
                "packing, or warehouse operations. Use when there are fulfillment "
                "issues, delays, or when the order needs special handling."
            ),
            "parameters": _MESSAGE_PARAMS,
        },
    },
    {
        "type": "function",
        "function": {
            "name": "message_payments_team",
            "description": (
                "Send a message to the payments team about payment issues, "
                "refund requests, or billing disputes. Use for payment failures, "
                "chargebacks, or refund processing."
            ),
            "parameters": _MESSAGE_PARAMS,
        },
    },
    {
        "type": "function",
        "function": {
            "name": "message_logistics_team",
            "description": (
                "Send a message to the logistics team about shipping, delivery, "
                "or carrier issues. Use for shipment delays, lost packages, or "
                "routing problems."
            ),
            "parameters": _MESSAGE_PARAMS,
        },
    },
    {
        "type": "function",
        "function": {
            "name": "message_customer",
            "description": (
                "Send a message to the customer about their order. Use to "
                "provide updates, request information, or notify of issues "
                "that directly affect the customer."
            ),
            "parameters": _MESSAGE_PARAMS,
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_internal_note",
            "description": (
                "Create an internal note visible to the support team. Use to "
                "document reasoning, flag concerns, or record decisions for "
                "human review without contacting any team."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "note": {
                        "type": "string",
                        "description": "The note content to record.",
                    },
                    "reasoning": {
                        "type": "string",
                        "description": "Why you are creating this note.",
                    },
                },
                "required": ["note", "reasoning"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "sleep",
            "description": (
                "Stop processing and sleep until the next scheduled check. "
                "You MUST call this when you have finished all actions for "
                "this cycle. Do not call other tools after sleep."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "duration_minutes": {
                        "type": "integer",
                        "description": "How many minutes to sleep before the next check.",
                    },
                    "reason": {
                        "type": "string",
                        "description": "Why you are sleeping (what you are waiting for).",
                    },
                    "next_check_focus": {
                        "type": "string",
                        "description": (
                            "What to look for on the next wake-up. This guides the "
                            "classifier when deciding whether incoming events warrant "
                            "an early wake."
                        ),
                    },
                },
                "required": ["duration_minutes", "reason", "next_check_focus"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_state",
            "description": (
                "Update a field in the run state. Use to record your assessment "
                "of the order situation, update order_status, or store any "
                "information needed for the next cycle."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {
                        "type": "string",
                        "description": "The state field name to update.",
                    },
                    "value": {
                        "type": "string",
                        "description": "The new value as a string.",
                    },
                    "reasoning": {
                        "type": "string",
                        "description": "Why you are updating this state field.",
                    },
                },
                "required": ["key", "value"],
            },
        },
    },
]

_TOOL_MAP: dict[str, dict] = {t["function"]["name"]: t for t in AVAILABLE_TOOLS}


def get_tools_for_supervisor(available_actions: list[str], default_sleep_minutes: int = 60) -> list[dict]:
    """Return tool dicts for the given actions, always including sleep and update_state."""
    always_included = {"sleep", "update_state"}
    requested = set(available_actions) | always_included
    
    tools = []
    for t in AVAILABLE_TOOLS:
        name = t["function"]["name"]
        if name in requested:
            # Deep copy or rebuild to avoid mutating global AVAILABLE_TOOLS
            tool_copy = json.loads(json.dumps(t))
            if name == "sleep":
                tool_copy["function"]["description"] = (
                    f"Stop processing and sleep until the next scheduled check. "
                    f"The DEFAULT duration for this supervisor is {default_sleep_minutes} minutes. "
                    f"You MUST call this when you have finished all actions for this cycle."
                )
            tools.append(tool_copy)
    return tools
