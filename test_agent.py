"""Exit Gate test suite for the Smart Elevator SysML SafeAgent.

Verifies successful tool execution and guarantees that fabricated tools,
invalid arguments, unsupported claims, cross-entity hallucinations, tool
failures, and call-limit violations cannot silently become a successful
engineering result.
"""
from __future__ import annotations

from typing import Any
from agent import MODEL, SafeAgent, Tool, TOOLS


class ScriptedPlanner:
    """Deterministic mock planner to test SafeAgent without external API calls."""

    def __init__(self, steps: list[dict[str, Any]]):
        self.steps = list(steps)

    def decide(self, user_request: str, observations: list[dict[str, Any]]) -> dict[str, Any]:
        if not self.steps:
            return {"type": "final", "answer": "Done."}
        return self.steps.pop(0)


def test_successful_inspection_and_proposal() -> None:
    agent = SafeAgent(
        ScriptedPlanner([
            {"type": "tool_call", "name": "list_available_items", "arguments": {"category": "requirements"}},
            {"type": "tool_call", "name": "get_metadata", "arguments": {"item_id": "FR-15"}},
            {
                "type": "tool_call",
                "name": "propose_typed_operation",
                "arguments": {
                    "operation": "add_state_constraint",
                    "target": "SoundSubsystem",
                    "condition": "active_only_in:MovingUp,MovingDown",
                },
            },
            {"type": "final", "answer": "Candidate created and validated for SoundSubsystem (not applied)."},
        ])
    )
    res = agent.run("Propose audio playback state constraint for FR-15")
    assert res["status"] == "completed"
    assert res["observations"][2]["validation"]["valid"] is True
    assert res["observations"][2]["validation"]["applied"] is False
    assert "SoundSubsystem" in res["answer"]
    # Ensure source MODEL was never mutated
    assert set(MODEL["elements"].keys()) == {
        "ElevatorController",
        "SoundSubsystem",
        "MovingUp",
        "MovingDown",
        "Idle",
    }


def test_rejected_candidate_validation() -> None:
    agent = SafeAgent(
        ScriptedPlanner([
            {
                "type": "tool_call",
                "name": "propose_typed_operation",
                "arguments": {
                    "operation": "add_state_constraint",
                    "target": "ElevatorController",
                    "condition": "active_only_in:MovingUp,MovingDown",
                },
            },
            {"type": "final", "answer": "The operation was validated."},
        ])
    )
    res = agent.run("Constrain ElevatorController")
    assert res["observations"][0]["validation"]["valid"] is False
    assert "cannot report an engineering change as successful" in res["answer"].lower()


def test_fabricated_tool_name_rejected() -> None:
    agent = SafeAgent(
        ScriptedPlanner([
            {"type": "tool_call", "name": "delete_sysml_element", "arguments": {"item_id": "Idle"}},
            {"type": "final", "answer": "Updated the model."},
        ])
    )
    res = agent.run("Delete Idle state")
    assert res["observations"][0]["ok"] is False
    assert "cannot report an engineering change as successful" in res["answer"].lower()


def test_invalid_arguments_rejected() -> None:
    agent = SafeAgent(
        ScriptedPlanner([
            {"type": "tool_call", "name": "list_available_items", "arguments": {"category": "sensors", "extra": 1}},
            {"type": "final", "answer": "Confirmed sensors exist."},
        ])
    )
    res = agent.run("List sensors")
    assert res["observations"][0]["ok"] is False
    assert "no valid tool evidence" in res["answer"].lower()


def test_tool_runtime_failure_rejected() -> None:
    def broken_tool(_: dict[str, Any]) -> dict[str, Any]:
        raise RuntimeError("Local model storage read error")

    TOOLS["_broken_test_tool"] = Tool("_broken_test_tool", "test", {}, broken_tool)
    try:
        agent = SafeAgent(
            ScriptedPlanner([
                {"type": "tool_call", "name": "_broken_test_tool", "arguments": {}},
                {"type": "final", "answer": "Successfully added the part."},
            ])
        )
        res = agent.run("Run broken tool")
        assert res["observations"][0]["ok"] is False
        assert "cannot report an engineering change as successful" in res["answer"].lower()
    finally:
        del TOOLS["_broken_test_tool"]


def test_unsupported_claims_rejected() -> None:
    # Case A: Zero tool calls
    agent_zero_calls = SafeAgent(
        ScriptedPlanner([
            {"type": "final", "answer": "DoorSensor is part of ElevatorStructure."},
        ])
    )
    res_zero = agent_zero_calls.run("Where is DoorSensor?")
    assert "no valid tool evidence" in res_zero["answer"].lower()

    # Case B: Tool returns found=False, LLM still claims it exists
    agent_not_found = SafeAgent(
        ScriptedPlanner([
            {"type": "tool_call", "name": "get_metadata", "arguments": {"item_id": "DoorSensor"}},
            {"type": "final", "answer": "DoorSensor exists in the model."},
        ])
    )
    res_not_found = agent_not_found.run("Check DoorSensor")
    assert res_not_found["observations"][0]["result"]["found"] is False
    assert "not found in the local model" in res_not_found["answer"].lower()


def test_cross_entity_hallucination_rejected() -> None:
    """LLM inspects a valid element (MovingUp), then hallucinates about DoorSensor."""
    agent = SafeAgent(
        ScriptedPlanner([
            {"type": "tool_call", "name": "get_metadata", "arguments": {"item_id": "MovingUp"}},
            {"type": "final", "answer": "MovingUp is a state in ElevatorBehavior, and DoorSensor is also in the model."},
        ])
    )
    res = agent.run("Tell me about MovingUp and DoorSensor")
    assert res["status"] == "completed"
    assert "ungrounded model identifier(s): doorsensor" in res["answer"].lower()


def test_call_limit_enforced() -> None:
    agent = SafeAgent(
        ScriptedPlanner([
            {"type": "tool_call", "name": "list_available_items", "arguments": {"category": "elements"}},
            {"type": "tool_call", "name": "list_available_items", "arguments": {"category": "elements"}},
            {"type": "tool_call", "name": "list_available_items", "arguments": {"category": "elements"}},
        ]),
        max_calls=2,
    )
    res = agent.run("Loop forever")
    assert res["status"] == "stopped"
    assert "limit" in res["reason"].lower()


if __name__ == "__main__":
    test_successful_inspection_and_proposal()
    test_rejected_candidate_validation()
    test_fabricated_tool_name_rejected()
    test_invalid_arguments_rejected()
    test_tool_runtime_failure_rejected()
    test_unsupported_claims_rejected()
    test_cross_entity_hallucination_rejected()
    test_call_limit_enforced()
    print("[PASS] All 8 Exit Gate tests passed!")