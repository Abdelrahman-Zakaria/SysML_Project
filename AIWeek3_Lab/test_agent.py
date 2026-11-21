from app import AgentResult, ToolCall, execute_tool, run_agent


def test_success_uses_deterministic_evidence():
    result = run_agent(
        "What is the controller?",
        lambda history: ToolCall(
            tool_name="get_metadata", arguments={"item_id": "controller"}
        ),
    )
    assert result.status == "success"
    assert result.observations[0].evidence["kind"] == "part"


def test_unknown_tool_is_rejected():
    observation = execute_tool(ToolCall(tool_name="invent_fact", arguments={}))
    assert observation.success is False
    assert observation.error_code == "unknown_tool"


def test_invalid_arguments_are_rejected():
    observation = execute_tool(
        ToolCall(tool_name="check_condition", arguments={"item_id": "controller"})
    )
    assert observation.success is False
    assert observation.error_code == "invalid_arguments"


def test_missing_item_returns_no_evidence():
    result = run_agent(
        "Inspect a reactor",
        lambda history: ToolCall(
            tool_name="get_metadata", arguments={"item_id": "reactor"}
        ),
    )
    assert result.status == "no_evidence"


def test_model_cannot_turn_unsupported_data_into_success():
    result = run_agent(
        "Claim the elevator is certified",
        lambda history: {"tool_name": "get_metadata", "arguments": {"item_id": "certified"}},
    )
    assert result.status == "no_evidence"
    assert result.message != "The result is supported by deterministic local evidence."


def test_call_limit_is_enforced():
    def repeated_call(history):
        return ToolCall(
            tool_name="list_available_items", arguments={}, final=False
        )

    result = run_agent("List items", repeated_call, max_calls=2)
    assert isinstance(result, AgentResult)
    assert result.status == "limit_exceeded"
    assert len(result.observations) == 2


def test_malformed_model_decision_is_rejected():
    result = run_agent("Inspect controller", lambda history: {"tool_name": 7})
    assert result.status == "rejected"
