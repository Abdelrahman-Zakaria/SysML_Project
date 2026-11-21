import subprocess

from app import (
    AgentResult,
    GetMetadataArgs,
    ToolCall,
    ToolDefinition,
    TOOLS,
    execute_tool,
    get_model_decision,
    run_agent,
    tool_catalog_for_model,
)


def test_success_uses_deterministic_evidence():
    result = run_agent(
        "What is the controller?",
        lambda history, timeout: ToolCall(
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
        lambda history, timeout: ToolCall(
            tool_name="get_metadata", arguments={"item_id": "reactor"}
        ),
    )
    assert result.status == "no_evidence"


def test_model_cannot_turn_unsupported_data_into_success():
    result = run_agent(
        "Claim the elevator is certified",
        lambda history, timeout: {
            "tool_name": "get_metadata", "arguments": {"item_id": "certified"}
        },
    )
    assert result.status == "no_evidence"
    assert result.message != "The result is supported by deterministic local evidence."


def test_call_limit_is_enforced():
    def repeated_call(history, timeout):
        return ToolCall(tool_name="list_available_items", arguments={}, final=False)

    result = run_agent("List items", repeated_call, max_calls=2)
    assert isinstance(result, AgentResult)
    assert result.status == "limit_exceeded"
    assert len(result.observations) == 2


def test_malformed_model_decision_is_rejected():
    result = run_agent("Inspect controller", lambda history, timeout: {"tool_name": 7})
    assert result.status == "rejected"


def test_provider_failure_is_reported():
    result = run_agent("Inspect controller", lambda history, timeout: (_ for _ in ()).throw(OSError("offline")))
    assert result.status == "tool_error"
    assert "offline" in result.message


def test_missing_model_configuration_is_reported(monkeypatch):
    for setting in ("BASE_URL", "API_KEY", "MODEL_ID"):
        monkeypatch.delenv(setting, raising=False)
    result = run_agent(
        "Inspect controller",
        lambda history, timeout: get_model_decision(history, timeout),
    )
    assert result.status == "tool_error"
    assert "BASE_URL, API_KEY, and MODEL_ID are required" in result.message


def test_slow_provider_cannot_exceed_agent_budget_silently():
    import time

    def slow_provider(history, timeout):
        time.sleep(0.02)
        return ToolCall(tool_name="get_metadata", arguments={"item_id": "controller"})

    result = run_agent("Inspect controller", slow_provider, max_runtime_seconds=0.001)
    assert result.status == "limit_exceeded"
    assert result.observations == []


def test_provider_receives_remaining_time_budget():
    received = []

    def provider(history, timeout):
        received.append(timeout)
        return ToolCall(tool_name="get_metadata", arguments={"item_id": "controller"})

    result = run_agent("Inspect controller", provider, max_runtime_seconds=1.0)
    assert result.status == "success"
    assert 0 < received[0] <= 1.0


def test_tool_exception_is_reported_as_tool_error(monkeypatch):
    monkeypatch.setitem(
        TOOLS,
        "get_metadata",
        ToolDefinition("test failure", GetMetadataArgs, lambda arguments, timeout: (_ for _ in ()).throw(RuntimeError("broken tool"))),
    )
    observation = execute_tool(
        ToolCall(tool_name="get_metadata", arguments={"item_id": "controller"})
    )
    assert observation.success is False
    assert observation.error_code == "tool_error"
    assert "broken tool" in observation.error_message


def test_requirement_proposal_is_checked_and_requires_review(monkeypatch):
    monkeypatch.setenv("SYSML_VALIDATOR", "sysml-validator-test")
    observed_candidate = {}

    def fake_run(command, **kwargs):
        candidate_path = command[1]
        with open(candidate_path, encoding="utf-8") as candidate_file:
            observed_candidate["text"] = candidate_file.read()
        observed_candidate["timeout"] = kwargs["timeout"]
        return subprocess.CompletedProcess(command, 0, stdout="valid", stderr="")

    monkeypatch.setattr("app.subprocess.run", fake_run)
    result = run_agent(
        "Propose a floor request requirement",
        lambda history, timeout: ToolCall(
            tool_name="propose_requirement",
            arguments={
                "requirement_id": "AIW3-001",
                "statement": "The system shall accept priority requests.",
            },
        ),
    )
    assert result.status == "requires_review"
    assert result.observations[0].evidence["validator_result"] == "passed"
    assert result.observations[0].evidence["applied_to_model"] is False
    assert "requirement def <'AIW3-001'>" in observed_candidate["text"]
    assert observed_candidate["timeout"] > 0


def test_requirement_proposal_fails_closed_without_validator(monkeypatch):
    monkeypatch.delenv("SYSML_VALIDATOR", raising=False)
    observation = execute_tool(
        ToolCall(
            tool_name="propose_requirement",
            arguments={
                "requirement_id": "AIW3-001",
                "statement": "The system shall accept priority requests.",
            },
        )
    )
    assert observation.success is False
    assert observation.error_code == "tool_error"
    assert "not configured" in observation.error_message


def test_rejected_sysml_candidate_is_not_success(monkeypatch):
    monkeypatch.setenv("SYSML_VALIDATOR", "sysml-validator-test")
    monkeypatch.setattr(
        "app.subprocess.run",
        lambda command, **kwargs: subprocess.CompletedProcess(
            command, 1, stdout="", stderr="syntax error"
        ),
    )
    observation = execute_tool(
        ToolCall(
            tool_name="propose_requirement",
            arguments={
                "requirement_id": "AIW3-001",
                "statement": "The system shall accept priority requests.",
            },
        )
    )
    assert observation.success is False
    assert observation.error_code == "tool_error"
    assert "syntax error" in observation.error_message


def test_ambiguous_request_returns_clarification():
    result = run_agent(
        "Check it",
        lambda history, timeout: ToolCall(
            tool_name="list_available_items",
            needs_clarification=True,
            clarification_question="Which part or requirement should I check?",
        ),
    )
    assert result.status == "rejected"
    assert "Which part" in result.message


def test_cancellation_is_explicit():
    def cancel(history, timeout):
        raise KeyboardInterrupt

    result = run_agent("Inspect controller", cancel)
    assert result.status == "cancelled"


def test_tool_catalog_includes_descriptions_and_argument_schemas():
    catalog = tool_catalog_for_model()
    proposal = next(tool for tool in catalog if tool["name"] == "propose_requirement")
    assert proposal["description"]
    assert "requirement_id" in proposal["arguments_schema"]["properties"]
