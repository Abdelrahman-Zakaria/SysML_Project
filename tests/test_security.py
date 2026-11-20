import pytest

from agent.agent import Agent
from agent.tool_registry import TOOL_REGISTRY


class FakePlanner:
    """
    A fake planner used to control the tool calls
    during security testing.
    """

    def __init__(self, plan):
        self.plan_data = plan

    def plan(self, user_request):
        return self.plan_data


# 1. Reject a fabricated tool name
def test_reject_unknown_tool():

    planner = FakePlanner({
        "calls": [
            {
                "tool_name": "delete_database",
                "arguments": {}
            }
        ]
    })

    agent = Agent(planner)

    result = agent.run("Delete the database")

    assert result["success"] is False
    assert result["error"] == "UNKNOWN_TOOL"


# 2. Reject invalid argument values
def test_reject_invalid_argument():

    planner = FakePlanner({
        "calls": [
            {
                "tool_name": "list_available_items",
                "arguments": {
                    "item_type": "Moon"
                }
            }
        ]
    })

    agent = Agent(planner)

    result = agent.run("List moon items")

    assert result["success"] is False
    assert result["error"] == "INVALID_ARGUMENT"


# 3. Reject missing required arguments
def test_reject_missing_argument():

    planner = FakePlanner({
        "calls": [
            {
                "tool_name": "get_metadata",
                "arguments": {}
            }
        ]
    })

    agent = Agent(planner)

    result = agent.run("Get metadata")

    assert result["success"] is False
    assert result["error"] == "MISSING_ARGUMENT"


# 4. Reject unexpected arguments
def test_reject_unexpected_argument():

    planner = FakePlanner({
        "calls": [
            {
                "tool_name": "get_metadata",
                "arguments": {
                    "element_id": "REQ-001",
                    "admin": "True"
                }
            }
        ]
    })

    agent = Agent(planner)

    result = agent.run("Get metadata")

    assert result["success"] is False
    assert result["error"] == "UNEXPECTED_ARGUMENT"


# 5. Enforce maximum tool call limit
def test_reject_excessive_tool_calls():

    calls = [
        {
            "tool_name": "list_available_items",
            "arguments": {
                "item_type": "Block"
            }
        }
        for _ in range(6)
    ]

    planner = FakePlanner({
        "calls": calls
    })

    agent = Agent(planner, max_tool_calls=5)

    result = agent.run("List blocks")

    assert result["success"] is False
    assert result["error"] == "TOOL_CALL_LIMIT_EXCEEDED"


# 6. Handle tool execution failure
def test_handle_tool_execution_failure(monkeypatch):

    def failing_tool(element_id):
        raise RuntimeError("Simulated tool failure")

    monkeypatch.setitem(
        TOOL_REGISTRY["get_metadata"],
        "function",
        failing_tool
    )

    planner = FakePlanner({
        "calls": [
            {
                "tool_name": "get_metadata",
                "arguments": {
                    "element_id": "REQ-001"
                }
            }
        ]
    })

    agent = Agent(planner)

    result = agent.run("Get metadata for REQ-001")

    assert result["success"] is False
    assert result["error"] == "TOOL_EXECUTION_FAILED"