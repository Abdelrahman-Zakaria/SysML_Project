import json
import os
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
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
    kind: Literal["part", "requirement"] = "part"
    limit: int = Field(default=20, ge=1, le=50)


class GetMetadataArgs(BaseModel):
    item_id: str = Field(min_length=1, max_length=80)


class CheckConditionArgs(BaseModel):
    item_id: str = Field(min_length=1, max_length=80)
    condition: Literal["exists", "has_requirement", "safe_for_motion"]


class ToolCall(BaseModel):
    tool_name: str = Field(min_length=1, max_length=80)
    arguments: dict[str, Any] = Field(default_factory=dict)
    final: bool = True


class ToolObservation(BaseModel):
    tool_name: str
    success: bool
    evidence: dict[str, Any] = Field(default_factory=dict)
    error_code: str | None = None
    error_message: str | None = None


class AgentResult(BaseModel):
    status: Literal[
        "success", "no_evidence", "rejected", "tool_error", "limit_exceeded"
    ]
    observations: list[ToolObservation] = Field(default_factory=list)
    message: str


@dataclass(frozen=True)
class ToolDefinition:
    argument_model: type[BaseModel]
    handler: Callable[[BaseModel], dict[str, Any]]


def list_available_items(arguments: BaseModel) -> dict[str, Any]:
    args = ListAvailableItemsArgs.model_validate(arguments)
    source = COMPONENTS if args.kind == "part" else REQUIREMENTS
    return {"items": list(source)[: args.limit], "kind": args.kind}


def get_metadata(arguments: BaseModel) -> dict[str, Any]:
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


def check_condition(arguments: BaseModel) -> dict[str, Any]:
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


TOOLS = {
    "list_available_items": ToolDefinition(ListAvailableItemsArgs, list_available_items),
    "get_metadata": ToolDefinition(GetMetadataArgs, get_metadata),
    "check_condition": ToolDefinition(CheckConditionArgs, check_condition),
}


def execute_tool(call: ToolCall) -> ToolObservation:
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
        evidence = definition.handler(arguments)
        return ToolObservation(tool_name=call.tool_name, success=True, evidence=evidence)
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
    except (TypeError, ValueError) as error:
        return ToolObservation(
            tool_name=call.tool_name,
            success=False,
            error_code="tool_error",
            error_message=str(error),
        )


DecisionProvider = Callable[[list[dict[str, Any]]], ToolCall]


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
        if time.monotonic() - started >= max_runtime_seconds:
            return AgentResult(
                status="limit_exceeded",
                observations=observations,
                message="The agent runtime limit was reached.",
            )
        try:
            call = ToolCall.model_validate(decision_provider(history))
        except (ValidationError, TypeError, ValueError) as error:
            return AgentResult(
                status="rejected",
                observations=observations,
                message=f"The model decision was rejected: {error}",
            )

        observation = execute_tool(call)
        observations.append(observation)
        history.append({"role": "tool", "content": observation.model_dump()})
        if not observation.success:
            status = "no_evidence" if observation.error_code == "no_evidence" else (
                "rejected" if observation.error_code in {"unknown_tool", "invalid_arguments"}
                else "tool_error"
            )
            return AgentResult(status=status, observations=observations,
                               message=observation.error_message or "Tool execution failed.")
        if call.final:
            return AgentResult(
                status="success",
                observations=observations,
                message="The result is supported by deterministic local evidence.",
            )

    return AgentResult(
        status="limit_exceeded",
        observations=observations,
        message="The maximum number of tool calls was reached.",
    )


def get_model_decision(request: str, history: list[dict[str, Any]]) -> ToolCall:
    base_url = os.getenv("BASE_URL")
    api_key = os.getenv("GEMINI_API_KEY")
    model_id = os.getenv("MODEL_ID")
    if not base_url or not api_key or not model_id:
        raise ValueError("BASE_URL, GEMINI_API_KEY, and MODEL_ID are required.")

    client = InferenceClient(base_url=base_url, api_key=api_key)
    response = client.chat_completion(
        model=model_id,
        messages=[
            {
                "role": "system",
                "content": (
                    "Choose exactly one allow-listed tool. Return only JSON with "
                    '{"tool_name":"...","arguments":{...}}. Never provide engineering '
                    "facts directly. Available tools: list_available_items, "
                    "get_metadata, check_condition. Set final=true when no more "
                    "evidence is needed."
                ),
            },
            *history,
            {"role": "user", "content": request},
        ],
        max_tokens=300,
    )
    if not response.choices:
        raise ValueError("The model returned no choices.")
    content = response.choices[0].message.content
    if not isinstance(content, str) or not content.strip():
        raise ValueError("The model returned an empty decision.")
    return ToolCall.model_validate_json(content)


if __name__ == "__main__":
    request = input("What should I inspect? ").strip()
    result = run_agent(request, lambda history: get_model_decision(request, history))
    print(json.dumps(result.model_dump(), indent=2))
