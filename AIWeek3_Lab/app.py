import json
import os
import subprocess
import tempfile
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from dotenv import load_dotenv
from huggingface_hub import InferenceClient
from pydantic import BaseModel, Field, ValidationError

load_dotenv()

MAX_CALLS = 3
MAX_RUNTIME_SECONDS = 10.0

COMPONENTS: dict[str, dict[str, str]] = {
    "controller": {
        "kind": "part",
        "description": "Schedules requests and coordinates elevator movement.",
        "requirement": "FR-01",
    },
    "motor_subsystem": {
        "kind": "part",
        "description": "Moves the elevator car between floors.",
        "requirement": "FR-03",
    },
    "door_subsystem": {
        "kind": "part",
        "description": "Controls opening, closing, and obstruction handling.",
        "requirement": "SR-01",
    },
    "safety_subsystem": {
        "kind": "part",
        "description": "Detects overloads and prevents unsafe motion.",
        "requirement": "SR-03",
    },
}

REQUIREMENTS = {
    "FR-01": "The system shall accept floor requests.",
    "FR-03": "The system shall transport passengers between floors.",
    "SR-01": "The system shall detect door obstruction.",
    "SR-03": "The system shall stop the elevator during a critical fault.",
}


class ListAvailableItemsArgs(BaseModel):
    kind: Literal["part", "requirement"] = Field(
        default="part", description="Whether to list parts or requirements."
    )
    limit: int = Field(default=20, ge=1, le=50, description="Maximum results.")


class GetMetadataArgs(BaseModel):
    item_id: str = Field(min_length=1, max_length=80, description="Known item ID.")


class CheckConditionArgs(BaseModel):
    item_id: str = Field(min_length=1, max_length=80, description="Known part ID.")
    condition: Literal["exists", "has_requirement", "safe_for_motion"] = Field(
        description="The deterministic condition to check."
    )


class ProposeRequirementArgs(BaseModel):
    requirement_id: str = Field(
        pattern=r"^AIW3-[0-9]{3}$",
        description="A new candidate ID in the AIW3-001 through AIW3-999 format.",
    )
    statement: str = Field(
        min_length=10,
        max_length=240,
        description="A concise SysML requirement statement beginning 'The system shall'.",
    )


class ToolCall(BaseModel):
    tool_name: str = Field(min_length=1, max_length=80)
    arguments: dict[str, Any] = Field(default_factory=dict)
    final: bool = True
    needs_clarification: bool = False
    clarification_question: str | None = Field(default=None, max_length=240)


class TokenUsage(BaseModel):
    prompt_tokens: int | None = Field(default=None, ge=0)
    completion_tokens: int | None = Field(default=None, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)


class ModelDecision(BaseModel):
    tool_call: ToolCall
    model_id: str | None = None
    token_usage: TokenUsage = Field(default_factory=TokenUsage)


class ModelOutputError(ValueError):
    """The provider returned an empty or structurally invalid decision."""


class ToolObservation(BaseModel):
    tool_name: str
    success: bool
    evidence: dict[str, Any] = Field(default_factory=dict)
    error_code: str | None = None
    error_message: str | None = None
    requires_review: bool = False


class AgentResult(BaseModel):
    status: Literal[
        "success", "no_evidence", "rejected", "tool_error", "limit_exceeded",
        "requires_review", "cancelled",
    ]
    observations: list[ToolObservation] = Field(default_factory=list)
    message: str
    metadata: dict[str, Any] = Field(
        default_factory=lambda: {
            "llm_token_usage": {
                "available": False,
                "prompt_tokens": None,
                "completion_tokens": None,
                "total_tokens": None,
                "calls": [],
            }
        }
    )


@dataclass(frozen=True)
class ToolDefinition:
    description: str
    argument_model: type[BaseModel]
    handler: Callable[[BaseModel, float], dict[str, Any]]


def list_available_items(arguments: BaseModel, timeout_seconds: float) -> dict[str, Any]:
    args = ListAvailableItemsArgs.model_validate(arguments)
    source = COMPONENTS if args.kind == "part" else REQUIREMENTS
    return {"items": list(source)[: args.limit], "kind": args.kind}


def get_metadata(arguments: BaseModel, timeout_seconds: float) -> dict[str, Any]:
    args = GetMetadataArgs.model_validate(arguments)
    if args.item_id in COMPONENTS:
        return {"item_id": args.item_id, **COMPONENTS[args.item_id]}
    if args.item_id in REQUIREMENTS:
        return {
            "item_id": args.item_id,
            "kind": "requirement",
            "description": REQUIREMENTS[args.item_id],
        }
    raise LookupError(f"No local evidence exists for item '{args.item_id}'.")


def check_condition(arguments: BaseModel, timeout_seconds: float) -> dict[str, Any]:
    args = CheckConditionArgs.model_validate(arguments)
    if args.item_id not in COMPONENTS:
        raise LookupError(f"No local evidence exists for item '{args.item_id}'.")
    if args.condition == "exists":
        value = True
    elif args.condition == "has_requirement":
        value = bool(COMPONENTS[args.item_id].get("requirement"))
    else:
        value = args.item_id != "safety_subsystem"
    return {"item_id": args.item_id, "condition": args.condition, "value": value}


def propose_requirement(arguments: BaseModel, timeout_seconds: float) -> dict[str, Any]:
    """Build a typed candidate and send it to a configured official validator."""
    args = ProposeRequirementArgs.model_validate(arguments)
    if not args.statement.startswith("The system shall "):
        raise ValueError("A proposal must be a requirement beginning 'The system shall'.")
    if "*/" in args.statement or "/*" in args.statement or "\n" in args.statement:
        raise ValueError("A proposal must be one plain-text sentence without comment delimiters.")
    validator = os.getenv("SYSML_VALIDATOR")
    if not validator:
        raise RuntimeError(
            "SYSML_VALIDATOR is not configured; the candidate was not validated."
        )

    candidate = (
        "package AIWeek3Candidate {\n"
        f"    requirement def <'{args.requirement_id}'> ProposedRequirement {{\n"
        f"        doc /* {args.statement} */\n"
        "    }\n"
        "}\n"
    )
    with tempfile.TemporaryDirectory(prefix="aiweek3_sysml_") as tmp_dir:
        candidate_path = Path(tmp_dir) / "candidate.sysml"
        candidate_path.write_text(candidate, encoding="utf-8")
        try:
            completed = subprocess.run(
                [validator, str(candidate_path)],
                capture_output=True,
                text=True,
                timeout=max(0.01, timeout_seconds),
                check=False,
            )
        except subprocess.TimeoutExpired as error:
            raise TimeoutError("The SysML validator exceeded the remaining time budget.") from error
        except OSError as error:
            raise RuntimeError(f"The configured SysML validator could not run: {error}") from error
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "No diagnostic was returned.").strip()
        raise ValueError(f"The SysML validator rejected the candidate: {detail[:500]}")
    return {
        "requirement_id": args.requirement_id,
        "candidate_sysml": candidate,
        "validator": Path(validator).name,
        "validator_result": "passed",
        "applied_to_model": False,
    }


TOOLS = {
    "list_available_items": ToolDefinition(
        "List known elevator parts or requirement IDs.",
        ListAvailableItemsArgs,
        list_available_items,
    ),
    "get_metadata": ToolDefinition(
        "Read deterministic metadata for a known part or requirement.",
        GetMetadataArgs,
        get_metadata,
    ),
    "check_condition": ToolDefinition(
        "Check a supported condition for a known elevator part.",
        CheckConditionArgs,
        check_condition,
    ),
    "propose_requirement": ToolDefinition(
        "Propose a typed SysML requirement candidate and validate it with the configured SysML compiler/validator; the proposal is never applied automatically.",
        ProposeRequirementArgs,
        propose_requirement,
    ),
}


def execute_tool(call: ToolCall, timeout_seconds: float = MAX_RUNTIME_SECONDS) -> ToolObservation:
    definition = TOOLS.get(call.tool_name)
    if definition is None:
        return ToolObservation(
            tool_name=call.tool_name,
            success=False,
            error_code="unknown_tool",
            error_message="The requested tool is not allow-listed.",
        )
    try:
        arguments = definition.argument_model.model_validate(call.arguments)
        evidence = definition.handler(arguments, timeout_seconds)
        return ToolObservation(
            tool_name=call.tool_name,
            success=True,
            evidence=evidence,
            requires_review=call.tool_name == "propose_requirement",
        )
    except ValidationError as error:
        return ToolObservation(
            tool_name=call.tool_name,
            success=False,
            error_code="invalid_arguments",
            error_message=str(error),
        )
    except LookupError as error:
        return ToolObservation(
            tool_name=call.tool_name,
            success=False,
            error_code="no_evidence",
            error_message=str(error),
        )
    except Exception as error:
        return ToolObservation(
            tool_name=call.tool_name,
            success=False,
            error_code="tool_error",
            error_message=f"{type(error).__name__}: {error}",
        )


DecisionProvider = Callable[[list[dict[str, Any]], float], Any]


def record_token_usage(target: dict[str, Any], decision: ModelDecision) -> None:
    usage = decision.token_usage
    call_usage = {
        "model_id": decision.model_id,
        "prompt_tokens": usage.prompt_tokens,
        "completion_tokens": usage.completion_tokens,
        "total_tokens": usage.total_tokens,
        "available": any(
            value is not None
            for value in (
                usage.prompt_tokens,
                usage.completion_tokens,
                usage.total_tokens,
            )
        ),
    }
    target["calls"].append(call_usage)
    for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
        value = call_usage[key]
        if value is not None:
            target[key] = (target[key] or 0) + value
    target["available"] = target["available"] or call_usage["available"]


def run_agent(
    request: str,
    decision_provider: DecisionProvider,
    *,
    max_calls: int = MAX_CALLS,
    max_runtime_seconds: float = MAX_RUNTIME_SECONDS,
) -> AgentResult:
    token_usage: dict[str, Any] = {
        "available": False,
        "prompt_tokens": None,
        "completion_tokens": None,
        "total_tokens": None,
        "calls": [],
    }

    def result(status: str, message: str, result_observations=None) -> AgentResult:
        return AgentResult(
            status=status,
            observations=result_observations or [],
            message=message,
            metadata={"llm_token_usage": token_usage},
        )

    if not request.strip():
        return result("rejected", "The request cannot be empty.")
    if max_calls < 1 or max_runtime_seconds <= 0:
        return result("rejected", "Agent limits must be positive.")

    started = time.monotonic()
    history: list[dict[str, Any]] = [{"role": "user", "content": request}]
    observations: list[ToolObservation] = []

    for _ in range(max_calls):
        remaining = max_runtime_seconds - (time.monotonic() - started)
        if remaining <= 0:
            return result("limit_exceeded", "The agent runtime limit was reached.", observations)
        try:
            proposed = decision_provider(history, remaining)
        except KeyboardInterrupt:
            return result("cancelled", "The agent run was cancelled.", observations)
        except ModelOutputError as error:
            return result("rejected", f"The model decision was rejected: {error}", observations)
        except Exception as error:
            elapsed = time.monotonic() - started
            status = "limit_exceeded" if elapsed >= max_runtime_seconds else "tool_error"
            return result(
                status,
                f"Model decision failed: {type(error).__name__}: {error}",
                observations,
            )

        if isinstance(proposed, ModelDecision):
            record_token_usage(token_usage, proposed)
            proposed = proposed.tool_call

        if time.monotonic() - started >= max_runtime_seconds:
            return result(
                "limit_exceeded",
                "The agent runtime limit was reached during model decision.",
                observations,
            )
        try:
            call = ToolCall.model_validate(proposed)
        except (ValidationError, TypeError, ValueError) as error:
            return result("rejected", f"The model decision was rejected: {error}", observations)

        if call.needs_clarification:
            return result(
                "rejected",
                call.clarification_question or "Please clarify the request.",
                observations,
            )

        remaining = max_runtime_seconds - (time.monotonic() - started)
        try:
            observation = execute_tool(call, max(0.0, remaining))
        except KeyboardInterrupt:
            return result("cancelled", "The agent run was cancelled during tool execution.", observations)
        observations.append(observation)
        history.append({"role": "tool", "content": observation.model_dump()})
        if time.monotonic() - started >= max_runtime_seconds:
            return result(
                "limit_exceeded",
                "The agent runtime limit was reached during tool execution.",
                observations,
            )
        if not observation.success:
            status = "no_evidence" if observation.error_code == "no_evidence" else (
                "rejected" if observation.error_code in {"unknown_tool", "invalid_arguments"}
                else "tool_error"
            )
            return result(
                status,
                observation.error_message or "Tool execution failed.",
                observations,
            )
        if call.final:
            if observation.requires_review:
                return result(
                    "requires_review",
                    "The candidate passed validation and is awaiting human review; it was not applied.",
                    observations,
                )
            return result(
                "success",
                "The result is supported by deterministic local evidence.",
                observations,
            )

    return result("limit_exceeded", "The maximum number of tool calls was reached.", observations)


def tool_catalog_for_model() -> list[dict[str, Any]]:
    return [
        {
            "name": name,
            "description": definition.description,
            "arguments_schema": definition.argument_model.model_json_schema(),
        }
        for name, definition in TOOLS.items()
    ]


def _reported_token_count(usage: Any, field: str) -> int | None:
    if isinstance(usage, dict):
        value = usage.get(field)
    else:
        value = getattr(usage, field, None)
    if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
        return value
    return None


def get_model_decision(
    history: list[dict[str, Any]],
    timeout_seconds: float,
) -> ModelDecision:
    base_url = os.getenv("BASE_URL")
    api_key = os.getenv("API_KEY")
    model_id = os.getenv("MODEL_ID")
    if not base_url or not api_key or not model_id:
        raise ValueError("BASE_URL, API_KEY, and MODEL_ID are required.")

    client = InferenceClient(
        base_url=base_url,
        api_key=api_key,
        timeout=timeout_seconds,
    )
    system_prompt = (
        "You are a bounded SysML inspection agent. Choose one tool from the catalog "
        "and return JSON matching {\"tool_name\": string, \"arguments\": object, "
        "\"final\": boolean, \"needs_clarification\": boolean, "
        "\"clarification_question\": string|null}. Do not assert engineering facts "
        "yourself. If the request is ambiguous, set needs_clarification=true. "
        "Requirement proposals are candidates only and require human review. Tool catalog: "
        + json.dumps(tool_catalog_for_model())
    )
    response = client.chat_completion(
        model=model_id,
        messages=[{"role": "system", "content": system_prompt}, *history],
        max_tokens=500,
        response_format={"type": "json_object"},
    )
    if not response.choices:
        raise ModelOutputError("The model returned no choices.")
    content = response.choices[0].message.content
    if not isinstance(content, str) or not content.strip():
        raise ModelOutputError("The model returned an empty decision.")
    try:
        tool_call = ToolCall.model_validate_json(content)
    except ValidationError as error:
        raise ModelOutputError(f"The model returned an invalid decision: {error}") from error
    usage = getattr(response, "usage", None)
    prompt_tokens = _reported_token_count(usage, "prompt_tokens")
    completion_tokens = _reported_token_count(usage, "completion_tokens")
    total_tokens = _reported_token_count(usage, "total_tokens")
    if total_tokens is None and prompt_tokens is not None and completion_tokens is not None:
        total_tokens = prompt_tokens + completion_tokens
    return ModelDecision(
        tool_call=tool_call,
        model_id=getattr(response, "model", model_id),
        token_usage=TokenUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
        ),
    )


def _display_token_count(value: int | None) -> str:
    return f"{value:,}" if value is not None else "not reported"


def format_console_result(result: AgentResult) -> str:
    lines = ["=== Agent result ===", f"Status: {result.status.replace('_', ' ').upper()}", result.message]

    for observation in result.observations:
        lines.extend(["", f"Tool: {observation.tool_name}"])
        if observation.success:
            if observation.evidence:
                lines.append("Evidence:")
                for key, value in observation.evidence.items():
                    label = key.replace("_", " ").capitalize()
                    if isinstance(value, bool):
                        shown_value = "Yes" if value else "No"
                    elif isinstance(value, list):
                        shown_value = ", ".join(str(item) for item in value)
                    elif value is None:
                        shown_value = "Not available"
                    else:
                        shown_value = str(value)
                    value_lines = shown_value.splitlines() or [""]
                    lines.append(f"  {label}: {value_lines[0]}")
                    lines.extend(f"    {part}" for part in value_lines[1:])
            if observation.requires_review:
                lines.append("Human review: required")
        else:
            lines.append(f"Outcome: {observation.error_code or 'tool_error'}")
            if observation.error_message:
                lines.append(f"Details: {observation.error_message}")

    usage = result.metadata.get("llm_token_usage", {})
    calls = usage.get("calls", [])
    available_calls = [call for call in calls if call.get("available")]
    lines.extend(["", "LLM token usage:"])
    if not available_calls:
        lines.append("  Token counts were not reported by the provider.")
    elif len(calls) == 1:
        call = calls[0]
        if call.get("model_id"):
            lines.append(f"  Model: {call['model_id']}")
        lines.append(
            "  "
            f"Prompt: {_display_token_count(call.get('prompt_tokens'))} | "
            f"Completion: {_display_token_count(call.get('completion_tokens'))} | "
            f"Total: {_display_token_count(call.get('total_tokens'))} tokens"
        )
    else:
        lines.append(
            "  Aggregate: "
            f"Prompt {_display_token_count(usage.get('prompt_tokens'))} | "
            f"Completion {_display_token_count(usage.get('completion_tokens'))} | "
            f"Total {_display_token_count(usage.get('total_tokens'))} tokens"
        )
        for index, call in enumerate(calls, start=1):
            model = f" ({call['model_id']})" if call.get("model_id") else ""
            lines.append(
                f"  Call {index}{model}: "
                f"prompt {_display_token_count(call.get('prompt_tokens'))}, "
                f"completion {_display_token_count(call.get('completion_tokens'))}, "
                f"total {_display_token_count(call.get('total_tokens'))}"
            )
    return "\n".join(lines)


if __name__ == "__main__":
    try:
        request = input("What should I inspect? ").strip()
    except (KeyboardInterrupt, EOFError):
        print(format_console_result(AgentResult(status="cancelled", message="Input was cancelled.")))
        raise SystemExit(0)
    result = run_agent(
        request,
        lambda history, timeout: get_model_decision(history, timeout),
    )
    print(format_console_result(result))
