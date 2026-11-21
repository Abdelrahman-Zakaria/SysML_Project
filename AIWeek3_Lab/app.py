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


def run_agent(
    request: str,
    decision_provider: DecisionProvider,
    *,
    max_calls: int = MAX_CALLS,
    max_runtime_seconds: float = MAX_RUNTIME_SECONDS,
) -> AgentResult:
    if not request.strip():
        return AgentResult(status="rejected", message="The request cannot be empty.")
    if max_calls < 1 or max_runtime_seconds <= 0:
        return AgentResult(status="rejected", message="Agent limits must be positive.")

    started = time.monotonic()
    history: list[dict[str, Any]] = [{"role": "user", "content": request}]
    observations: list[ToolObservation] = []

    for _ in range(max_calls):
        remaining = max_runtime_seconds - (time.monotonic() - started)
        if remaining <= 0:
            return AgentResult(
                status="limit_exceeded", observations=observations,
                message="The agent runtime limit was reached.",
            )
        try:
            proposed = decision_provider(history, remaining)
        except KeyboardInterrupt:
            return AgentResult(
                status="cancelled", observations=observations,
                message="The agent run was cancelled.",
            )
        except ModelOutputError as error:
            return AgentResult(
                status="rejected", observations=observations,
                message=f"The model decision was rejected: {error}",
            )
        except Exception as error:
            elapsed = time.monotonic() - started
            status = "limit_exceeded" if elapsed >= max_runtime_seconds else "tool_error"
            return AgentResult(
                status=status, observations=observations,
                message=f"Model decision failed: {type(error).__name__}: {error}",
            )

        if time.monotonic() - started >= max_runtime_seconds:
            return AgentResult(
                status="limit_exceeded", observations=observations,
                message="The agent runtime limit was reached during model decision.",
            )
        try:
            call = ToolCall.model_validate(proposed)
        except (ValidationError, TypeError, ValueError) as error:
            return AgentResult(
                status="rejected", observations=observations,
                message=f"The model decision was rejected: {error}",
            )

        if call.needs_clarification:
            return AgentResult(
                status="rejected", observations=observations,
                message=call.clarification_question or "Please clarify the request.",
            )

        remaining = max_runtime_seconds - (time.monotonic() - started)
        try:
            observation = execute_tool(call, max(0.0, remaining))
        except KeyboardInterrupt:
            return AgentResult(
                status="cancelled", observations=observations,
                message="The agent run was cancelled during tool execution.",
            )
        observations.append(observation)
        history.append({"role": "tool", "content": observation.model_dump()})
        if time.monotonic() - started >= max_runtime_seconds:
            return AgentResult(
                status="limit_exceeded", observations=observations,
                message="The agent runtime limit was reached during tool execution.",
            )
        if not observation.success:
            status = "no_evidence" if observation.error_code == "no_evidence" else (
                "rejected" if observation.error_code in {"unknown_tool", "invalid_arguments"}
                else "tool_error"
            )
            return AgentResult(
                status=status,
                observations=observations,
                message=observation.error_message or "Tool execution failed.",
            )
        if call.final:
            if observation.requires_review:
                return AgentResult(
                    status="requires_review", observations=observations,
                    message="The candidate passed validation and is awaiting human review; it was not applied.",
                )
            return AgentResult(
                status="success", observations=observations,
                message="The result is supported by deterministic local evidence.",
            )

    return AgentResult(
        status="limit_exceeded", observations=observations,
        message="The maximum number of tool calls was reached.",
    )


def tool_catalog_for_model() -> list[dict[str, Any]]:
    return [
        {
            "name": name,
            "description": definition.description,
            "arguments_schema": definition.argument_model.model_json_schema(),
        }
        for name, definition in TOOLS.items()
    ]


def get_model_decision(
    history: list[dict[str, Any]],
    timeout_seconds: float,
) -> ToolCall:
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
        return ToolCall.model_validate_json(content)
    except ValidationError as error:
        raise ModelOutputError(f"The model returned an invalid decision: {error}") from error


if __name__ == "__main__":
    try:
        request = input("What should I inspect? ").strip()
    except (KeyboardInterrupt, EOFError):
        print(json.dumps(AgentResult(status="cancelled", message="Input was cancelled.").model_dump(), indent=2))
        raise SystemExit(0)
    result = run_agent(
        request,
        lambda history, timeout: get_model_decision(history, timeout),
    )
    print(json.dumps(result.model_dump(), indent=2))
