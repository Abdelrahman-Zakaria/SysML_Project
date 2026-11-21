"""SysML v2 teaching agent with bounded tools and explicit observations.

The file is organized from data and schemas, through tools and the agent loop,
to the provider integration and user-facing output.
"""

import json
import os
import queue
import subprocess
import tempfile
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field, ValidationError, field_validator

load_dotenv()

MAX_CALLS = 3
MAX_RUNTIME_SECONDS = 300.0

# ---------------------------------------------------------------------------
# Example catalog and validated data shapes
# ---------------------------------------------------------------------------

# Stable local facts let students see that tool results come from Python data,
# not from a model's unsupported claims.
MODEL_ELEMENTS: dict[str, dict[str, str]] = {
    "ExamplePackage": {
        "kind": "package",
        "metaclass": "Package",
        "description": "A package that groups related SysML v2 model elements.",
        "documentation": "Example container for the other sample elements.",
    },
    "ExamplePart": {
        "kind": "part_definition",
        "metaclass": "PartDefinition",
        "description": "A reusable structural definition in a SysML v2 model.",
        "documentation": "Illustrates a typed part definition.",
    },
    "ExampleRequirement": {
        "kind": "requirement_definition",
        "metaclass": "RequirementDefinition",
        "description": "A requirement definition in a SysML v2 model.",
        "statement": "The system shall satisfy the example requirement.",
        "documentation": "Illustrates a requirement definition and its statement.",
    },
    "ExampleAction": {
        "kind": "action_definition",
        "metaclass": "ActionDefinition",
        "description": "A behavior definition in a SysML v2 model.",
        "documentation": "Illustrates an action definition.",
    },
}


# Pydantic schemas define the exact inputs each tool accepts. They also provide
# JSON schemas that are shown to the model before it selects a tool.
class ListAvailableItemsArgs(BaseModel):
    kind: Literal[
        "all", "package", "part_definition", "requirement_definition", "action_definition"
    ] = Field(
        default="all", description="Which kind of SysML v2 model element to list."
    )
    limit: int = Field(default=20, ge=1, le=50, description="Maximum results.")


class GetMetadataArgs(BaseModel):
    item_id: str = Field(min_length=1, max_length=80, description="Known item ID.")


class CheckConditionArgs(BaseModel):
    item_id: str = Field(min_length=1, max_length=80, description="Known model element ID.")
    condition: Literal["exists", "has_documentation", "is_definition"] = Field(
        description="The structural or documentation condition to check."
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

    @field_validator("requirement_id")
    @classmethod
    def reject_zero_requirement_id(cls, value: str) -> str:
        """Keep the pattern portable and disallow the reserved AIW3-000 ID."""
        if value == "AIW3-000":
            raise ValueError("The requirement ID range starts at AIW3-001.")
        return value


# The model returns this decision shape. The agent validates it before looking
# up or executing the requested tool.
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


# AgentEvent is the observable run log: it stores messages and actions, never
# hidden reasoning from the model.
class AgentEvent(BaseModel):
    kind: Literal[
        "user_message", "assistant_decision", "tool_call", "tool_result",
        "decision_error", "assistant_final",
    ]
    content: str | None = None
    tool_name: str | None = None
    arguments: dict[str, Any] | None = None
    decision: dict[str, Any] | None = None
    result: dict[str, Any] | None = None


class ToolObservation(BaseModel):
    """Typed result of one tool, including arguments and any explicit error."""

    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    success: bool
    evidence: dict[str, Any] = Field(default_factory=dict)
    error_code: str | None = None
    error_message: str | None = None
    requires_review: bool = False


class AgentResult(BaseModel):
    """Final outcome plus observations, event trace, and model usage metadata."""

    status: Literal[
        "success", "no_evidence", "rejected", "tool_error", "limit_exceeded",
        "requires_review", "cancelled",
    ]
    observations: list[ToolObservation] = Field(default_factory=list)
    events: list[AgentEvent] = Field(default_factory=list)
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
    """Pair a model-visible tool description and schema with its Python handler."""

    description: str
    argument_model: type[BaseModel]
    handler: Callable[[BaseModel, float], dict[str, Any]]


"""Deterministic tools: these read the local example catalog only."""


def list_available_items(arguments: BaseModel, timeout_seconds: float) -> dict[str, Any]:
    """Return IDs from the local catalog, filtered by element kind."""
    args = ListAvailableItemsArgs.model_validate(arguments)
    items = [
        item_id
        for item_id, item in MODEL_ELEMENTS.items()
        if args.kind == "all" or item["kind"] == args.kind
    ]
    return {"items": items[: args.limit], "kind": args.kind}


def get_metadata(arguments: BaseModel, timeout_seconds: float) -> dict[str, Any]:
    """Return catalog facts or raise when the requested ID has no evidence."""
    args = GetMetadataArgs.model_validate(arguments)
    if args.item_id in MODEL_ELEMENTS:
        return {"item_id": args.item_id, **MODEL_ELEMENTS[args.item_id]}
    raise LookupError(f"No local evidence exists for item '{args.item_id}'.")


def check_condition(arguments: BaseModel, timeout_seconds: float) -> dict[str, Any]:
    """Evaluate one supported condition using the local catalog only."""
    args = CheckConditionArgs.model_validate(arguments)
    if args.item_id not in MODEL_ELEMENTS:
        raise LookupError(f"No local evidence exists for item '{args.item_id}'.")
    item = MODEL_ELEMENTS[args.item_id]
    if args.condition == "exists":
        value = True
    elif args.condition == "has_documentation":
        value = bool(item.get("documentation"))
    else:
        value = item["kind"].endswith("_definition")
    return {"item_id": args.item_id, "condition": args.condition, "value": value}


# ---------------------------------------------------------------------------
# Official SysML validator and requirement proposal tool
# ---------------------------------------------------------------------------

def validate_with_official_sysml_kernel(candidate: str, timeout_seconds: float) -> None:
    """Send candidate text to the official local kernel and require success."""
    try:
        from jupyter_client import KernelManager
    except ImportError as error:
        raise RuntimeError(
            "jupyter_client is missing. Reinstall the AIWeek3 requirements and "
            "the official SysML kernel."
        ) from error

    # Share the agent's remaining budget across kernel startup and validation.
    deadline = time.monotonic() + timeout_seconds
    manager = KernelManager(kernel_name="sysml")
    client = None
    try:
        manager.start_kernel()
        client = manager.client()
        client.start_channels()
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("The SysML validator exceeded the remaining time budget.")
        client.wait_for_ready(timeout=remaining)

        # Jupyter returns a message ID so output and errors can be tied to this
        # exact candidate execution.
        message_id = client.execute(
            candidate,
            store_history=False,
            allow_stdin=False,
            stop_on_error=True,
        )
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("The SysML validator exceeded the remaining time budget.")
            try:
                message = client.get_iopub_msg(timeout=remaining)
            except queue.Empty as error:
                raise TimeoutError(
                    "The SysML validator exceeded the remaining time budget."
                ) from error
            if message.get("parent_header", {}).get("msg_id") != message_id:
                continue
            if message.get("msg_type") == "error":
                details = message.get("content", {})
                error_text = details.get("evalue") or "The SysML model was rejected."
                raise ValueError(f"Official SysML validation failed: {error_text}")
            if (
                message.get("msg_type") == "status"
                and message.get("content", {}).get("execution_state") == "idle"
            ):
                break

        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("The SysML validator exceeded the remaining time budget.")
        try:
            reply = client.get_shell_msg(timeout=remaining)
        except queue.Empty as error:
            raise TimeoutError(
                "The SysML validator exceeded the remaining time budget."
            ) from error
        while reply.get("parent_header", {}).get("msg_id") != message_id:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("The SysML validator exceeded the remaining time budget.")
            try:
                reply = client.get_shell_msg(timeout=remaining)
            except queue.Empty as error:
                raise TimeoutError(
                    "The SysML validator exceeded the remaining time budget."
                ) from error
        content = reply.get("content", {})
        if content.get("status") != "ok":
            error_text = content.get("evalue") or "The SysML model was rejected."
            raise ValueError(f"Official SysML validation failed: {error_text}")
    except (TimeoutError, ValueError):
        raise
    except Exception as error:
        raise RuntimeError(
            "Could not run the official OMG SysML v2 Pilot Implementation kernel. "
            "Install it with setup_official_sysml_kernel.ps1 and try again. "
            f"Details: {error}"
        ) from error
    finally:
        if client is not None:
            client.stop_channels()
        try:
            manager.shutdown_kernel(now=True)
        except Exception:
            pass


def propose_requirement(arguments: BaseModel, timeout_seconds: float) -> dict[str, Any]:
    """Build a typed candidate, validate it, and leave model changes to a person."""
    args = ProposeRequirementArgs.model_validate(arguments)
    if not args.statement.startswith("The system shall "):
        raise ValueError("A proposal must be a requirement beginning 'The system shall'.")
    if "*/" in args.statement or "/*" in args.statement or "\n" in args.statement:
        raise ValueError("A proposal must be one plain-text sentence without comment delimiters.")
    validator = os.getenv("SYSML_VALIDATOR")

    # Construct only the small SysML operation allowed by the typed schema.
    candidate = (
        "package AIWeek3Candidate {\n"
        f"    requirement def <'{args.requirement_id}'> ProposedRequirement {{\n"
        f"        doc /* {args.statement} */\n"
        "    }\n"
        "}\n"
    )
    if validator:
        # A configured wrapper receives a temporary .sysml file. With the
        # setting blank, the official Pilot Implementation kernel gets text.
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
        validator_name = Path(validator).name
    else:
        validate_with_official_sysml_kernel(candidate, timeout_seconds)
        validator_name = "OMG SysML v2 Pilot Implementation"
    return {
        "requirement_id": args.requirement_id,
        "candidate_sysml": candidate,
        "validator": validator_name,
        "validator_result": "passed",
        "applied_to_model": False,
    }


# The allow-list is the only route from a model decision to executable code.
TOOLS = {
    "list_available_items": ToolDefinition(
        "List available generic SysML v2 example packages, part definitions, requirement definitions, or action definitions.",
        ListAvailableItemsArgs,
        list_available_items,
    ),
    "get_metadata": ToolDefinition(
        "Read deterministic metadata for a known SysML v2 example model element.",
        GetMetadataArgs,
        get_metadata,
    ),
    "check_condition": ToolDefinition(
        "Check whether a known SysML v2 element exists, has documentation, or is a definition.",
        CheckConditionArgs,
        check_condition,
    ),
    "propose_requirement": ToolDefinition(
        "Propose a typed SysML requirement candidate and validate it with the configured validator (the official OMG SysML v2 Pilot kernel by default); the proposal is never applied automatically.",
        ProposeRequirementArgs,
        propose_requirement,
    ),
}


def execute_tool(call: ToolCall, timeout_seconds: float = MAX_RUNTIME_SECONDS) -> ToolObservation:
    """Allow-list, validate, execute, and convert failures into typed results."""
    definition = TOOLS.get(call.tool_name)
    if definition is None:
        return ToolObservation(
            tool_name=call.tool_name,
            arguments=call.arguments,
            success=False,
            error_code="unknown_tool",
            error_message="The requested tool is not allow-listed.",
        )
    validated_arguments = call.arguments
    try:
        arguments = definition.argument_model.model_validate(call.arguments)
        validated_arguments = arguments.model_dump()
        evidence = definition.handler(arguments, timeout_seconds)
        return ToolObservation(
            tool_name=call.tool_name,
            arguments=validated_arguments,
            success=True,
            evidence=evidence,
            requires_review=call.tool_name == "propose_requirement",
        )
    except ValidationError as error:
        return ToolObservation(
            tool_name=call.tool_name,
            arguments=call.arguments,
            success=False,
            error_code="invalid_arguments",
            error_message=str(error),
        )
    except LookupError as error:
        return ToolObservation(
            tool_name=call.tool_name,
            arguments=validated_arguments,
            success=False,
            error_code="no_evidence",
            error_message=str(error),
        )
    except Exception as error:
        return ToolObservation(
            tool_name=call.tool_name,
            arguments=validated_arguments,
            success=False,
            error_code="tool_error",
            error_message=f"{type(error).__name__}: {error}",
        )


DecisionProvider = Callable[[list[dict[str, Any]], float], Any]


"""Agent orchestration: validate each decision and retain observable results."""


def record_token_usage(target: dict[str, Any], decision: ModelDecision) -> None:
    """Accumulate provider-reported counts without estimating missing values."""
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
    """Run the inspectable request/decision/validate/execute/observe loop."""
    token_usage: dict[str, Any] = {
        "available": False,
        "prompt_tokens": None,
        "completion_tokens": None,
        "total_tokens": None,
        "calls": [],
    }
    events: list[AgentEvent] = [AgentEvent(kind="user_message", content=request)]

    def result(status: str, message: str, result_observations=None) -> AgentResult:
        """Build a final result and append its matching event to the trace."""
        # Every exit records a final answer/status alongside the events so far.
        events.append(
            AgentEvent(
                kind="assistant_final",
                content=message,
                result={"status": status},
            )
        )
        return AgentResult(
            status=status,
            observations=result_observations or [],
            events=events,
            message=message,
            metadata={"llm_token_usage": token_usage},
        )

    if not request.strip():
        return result("rejected", "The request cannot be empty.")
    if max_calls < 1 or max_runtime_seconds <= 0:
        return result("rejected", "Agent limits must be positive.")

    started = time.monotonic()
    # This is standard chat history. Each function call below is paired with a
    # tool result using the same call ID, so the next decision sees both.
    history: list[dict[str, Any]] = [{"role": "user", "content": request}]
    observations: list[ToolObservation] = []

    for _ in range(max_calls):
        remaining = max_runtime_seconds - (time.monotonic() - started)
        if remaining <= 0:
            return result("limit_exceeded", "The agent runtime limit was reached.", observations)
        # Ask for one decision, passing only the runtime budget that remains.
        try:
            proposed = decision_provider(history, remaining)
        except KeyboardInterrupt:
            return result("cancelled", "The agent run was cancelled.", observations)
        except ModelOutputError as error:
            events.append(AgentEvent(kind="decision_error", content=str(error)))
            return result("rejected", f"The model decision was rejected: {error}", observations)
        except Exception as error:
            elapsed = time.monotonic() - started
            status = "limit_exceeded" if elapsed >= max_runtime_seconds else "tool_error"
            events.append(
                AgentEvent(
                    kind="decision_error",
                    content=f"{type(error).__name__}: {error}",
                )
            )
            return result(
                status,
                f"Model decision failed: {type(error).__name__}: {error}",
                observations,
            )

        # Keep token accounting separate from the actual tool-call payload.
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
            events.append(AgentEvent(kind="decision_error", content=str(error)))
            return result("rejected", f"The model decision was rejected: {error}", observations)

        if call.needs_clarification:
            events.append(
                AgentEvent(
                    kind="assistant_decision",
                    decision=call.model_dump(),
                )
            )
            return result(
                "rejected",
                call.clarification_question or "Please clarify the request.",
                observations,
            )

        remaining = max_runtime_seconds - (time.monotonic() - started)
        # Keep the model's decision and arguments in the conversation history.
        # They are plain chat messages rather than synthetic OpenAI tool-call
        # messages, since Gemini requires provider-generated thought signatures
        # when native function-call messages are replayed.
        events.append(
            AgentEvent(
                kind="tool_call",
                tool_name=call.tool_name,
                arguments=call.arguments,
                decision=call.model_dump(),
            )
        )
        history.append(
            {
                "role": "assistant",
                "content": "Tool decision: " + json.dumps(call.model_dump()),
            }
        )
        try:
            observation = execute_tool(call, max(0.0, remaining))
        except KeyboardInterrupt:
            events.append(
                AgentEvent(
                    kind="tool_result",
                    tool_name=call.tool_name,
                    arguments=call.arguments,
                    result={"success": False, "error_code": "cancelled"},
                )
            )
            return result("cancelled", "The agent run was cancelled during tool execution.", observations)
        # The result stays in history for follow-up decisions without requiring
        # a provider-specific tool-call signature.
        observations.append(observation)
        observation_data = observation.model_dump()
        events.append(
            AgentEvent(
                kind="tool_result",
                tool_name=observation.tool_name,
                arguments=observation.arguments,
                result=observation_data,
            )
        )
        history.append(
            {
                "role": "user",
                "content": "Tool result: " + json.dumps(observation_data),
            }
        )
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


"""Provider integration: send chat history and parse a typed decision."""


def tool_catalog_for_model() -> list[dict[str, Any]]:
    """Expose tool names, descriptions, and argument schemas to the model."""
    return [
        {
            "name": name,
            "description": definition.description,
            "arguments_schema": definition.argument_model.model_json_schema(),
        }
        for name, definition in TOOLS.items()
    ]


def _reported_token_count(usage: Any, field: str) -> int | None:
    """Read a non-negative count when the provider includes it in its reply."""
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
    """Call the configured chat endpoint and parse its structured decision."""
    base_url = os.getenv("BASE_URL")
    api_key = os.getenv("API_KEY")
    model_id = os.getenv("MODEL_ID")
    if not base_url or not api_key or not model_id:
        raise ValueError("BASE_URL, API_KEY, and MODEL_ID are required.")

    client = OpenAI(
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
    response = client.chat.completions.create(
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
    """Format a provider token count, or mark it as unavailable."""
    return f"{value:,}" if value is not None else "not reported"


# ---------------------------------------------------------------------------
# Console rendering and command-line entry point
# ---------------------------------------------------------------------------

def format_console_result(result: AgentResult) -> str:
    """Render the structured result as a readable summary instead of raw JSON."""
    lines = ["=== Agent result ===", f"Status: {result.status.replace('_', ' ').upper()}", result.message]

    for observation in result.observations:
        lines.extend(["", f"Tool: {observation.tool_name}"])
        if observation.arguments:
            lines.append("Arguments:")
            for key, value in observation.arguments.items():
                label = key.replace("_", " ").capitalize()
                if isinstance(value, list):
                    shown_value = ", ".join(str(item) for item in value)
                else:
                    shown_value = str(value)
                lines.append(f"  {label}: {shown_value}")
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
    print("=== SysML v2 Model Agent ===")
    print("I can help you:")
    print("- List generic SysML v2 model elements by kind.")
    print("- Inspect a package, part, requirement, or action definition.")
    print("- Check whether an element exists, has documentation, or is a definition.")
    print("- Propose a SysML requirement for validation and human review.")
    print("Example: What kind of element is ExampleRequirement?")
    print("Requirement proposals are never applied automatically.")
    print()
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
