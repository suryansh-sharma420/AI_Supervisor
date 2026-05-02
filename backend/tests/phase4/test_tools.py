import pytest

from app.agent.tools import (
    AVAILABLE_TOOLS,
    BUSINESS_ACTION_TOOLS,
    get_tools_for_supervisor,
)


def test_get_tools_all_actions_returns_7() -> None:
    tools = get_tools_for_supervisor(BUSINESS_ACTION_TOOLS)
    assert len(tools) == 7


def test_get_tools_subset_always_includes_sleep_and_update_state() -> None:
    tools = get_tools_for_supervisor(["message_customer"])
    names = {t["function"]["name"] for t in tools}
    assert "sleep" in names
    assert "update_state" in names
    assert "message_customer" in names
    # others should not be present
    assert "message_fulfillment_team" not in names


def test_every_tool_has_required_keys() -> None:
    for tool in AVAILABLE_TOOLS:
        assert "type" in tool
        assert "function" in tool
        fn = tool["function"]
        assert "name" in fn
        assert "description" in fn
        assert "parameters" in fn


def test_sleep_tool_has_required_parameters() -> None:
    sleep_tool = next(t for t in AVAILABLE_TOOLS if t["function"]["name"] == "sleep")
    params = sleep_tool["function"]["parameters"]["properties"]
    assert "duration_minutes" in params
    assert "reason" in params
    assert "next_check_focus" in params
    required = sleep_tool["function"]["parameters"]["required"]
    assert "duration_minutes" in required
    assert "reason" in required
    assert "next_check_focus" in required


def test_business_action_tools_have_message_and_reasoning() -> None:
    for tool in AVAILABLE_TOOLS:
        name = tool["function"]["name"]
        if name not in BUSINESS_ACTION_TOOLS:
            continue
        props = tool["function"]["parameters"]["properties"]
        # message_fulfillment/payments/logistics/customer have "message"
        # create_internal_note has "note"
        if name == "create_internal_note":
            assert "note" in props
        else:
            assert "message" in props
        assert "reasoning" in props
