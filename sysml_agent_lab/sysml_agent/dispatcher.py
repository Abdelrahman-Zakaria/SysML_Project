"""Milestone 2 - the single entry point for tool calls.

Pipeline: tool name in registry -> arguments valid -> execute inside try/except
-> result checked. Every outcome is a DispatchEnvelope; nothing escapes as an
exception (except KeyboardInterrupt / SystemExit, which are deliberately not
swallowed).

Status meanings
  OK          the tool ran and its result is positive (ok / passed).
  REJECTED    the call was refused: unknown tool, bad arguments, missing
              prerequisite, or the tool ran and returned a negative verdict
              (the typed result is attached so the reason is visible).
  TOOL_ERROR  infrastructure failure: exception, wrong return type, or a
              result that is not well-formed.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from .registry import DEFAULT_REGISTRY, ToolContext, ToolRegistry
from .results import Issue, IssueCode
from .schema import validate_args


class Status(str, Enum):
    OK = "OK"
    REJECTED = "REJECTED"
    TOOL_ERROR = "TOOL_ERROR"


@dataclass(frozen=True)
class DispatchEnvelope:
    status: Status
    tool_name: str
    result: Optional[object] = None
    issues: tuple = ()

    def __post_init__(self) -> None:
        # An envelope cannot be built in a state that lies about the outcome.
        if not isinstance(self.status, Status):
            raise ValueError("status must be a Status member")
        if self.status is Status.OK:
            if self.result is None:
                raise ValueError("an OK envelope requires a tool result")
        elif not self.issues:
            raise ValueError(f"a {self.status.value} envelope requires at least one issue")

    @property
    def ok(self) -> bool:
        return self.status is Status.OK


def _display_name(tool_name: object) -> str:
    if isinstance(tool_name, str):
        return tool_name[:64]
    return f"<{type(tool_name).__name__}>"


def dispatch(tool_name: object, raw_args: object, context: ToolContext,
             registry: ToolRegistry = DEFAULT_REGISTRY) -> DispatchEnvelope:
    name = _display_name(tool_name)

    def refuse(status: Status, *issues: Issue, result: object = None) -> DispatchEnvelope:
        return DispatchEnvelope(status, name, result, tuple(issues))

    # 1. tool name
    spec = registry.get(tool_name) if isinstance(tool_name, str) else None
    if spec is None:
        return refuse(Status.REJECTED, Issue(
            IssueCode.UNKNOWN_TOOL,
            f"Unknown tool {name!r}. Available tools: {list(registry.names())}."))

    # 2. arguments (untrusted)
    args, issues = validate_args(spec.schema, raw_args)
    if issues:
        return DispatchEnvelope(Status.REJECTED, name, None, issues)

    # 3. harness-side preconditions
    if not isinstance(context, ToolContext):
        return refuse(Status.TOOL_ERROR, Issue(
            IssueCode.INVALID_INPUT,
            f"Harness error: context must be ToolContext, got {type(context).__name__}."))
    if spec.needs_candidate and context.candidate is None:
        return refuse(Status.REJECTED, Issue(
            IssueCode.NO_CANDIDATE,
            "No candidate exists yet. Call propose_operation first."))

    # 4. execute + interpret, never letting an exception escape
    try:
        if spec.normalize is not None:
            args, issues = spec.normalize(args)
            if issues:
                return DispatchEnvelope(Status.REJECTED, name, None, issues)

        result = spec.func(*spec.bind(context, args))

        if not isinstance(result, spec.result_type):
            return refuse(Status.TOOL_ERROR, Issue(
                IssueCode.BAD_TOOL_RESULT,
                f"Tool '{name}' returned {type(result).__name__}, "
                f"expected {spec.result_type.__name__}."))
        result_issues = tuple(result.issues)
        if not all(isinstance(i, Issue) for i in result_issues):
            return refuse(Status.TOOL_ERROR, Issue(
                IssueCode.BAD_TOOL_RESULT,
                f"Tool '{name}' returned a malformed issue list."))
        positive = bool(spec.is_positive(result))
    except Exception as exc:  # noqa: BLE001 - this is the safety net by design
        return refuse(Status.TOOL_ERROR, Issue(
            IssueCode.TOOL_EXCEPTION,
            f"Tool '{name}' raised {type(exc).__name__}: {str(exc)[:200]}"))

    if positive:
        return DispatchEnvelope(Status.OK, name, result, result_issues)

    # Negative verdict: always carry an explanation, never a silent failure.
    if not result_issues:
        result_issues = (Issue(IssueCode.UNEXPLAINED_FAILURE,
                               f"Tool '{name}' reported failure without any issue."),)
    return DispatchEnvelope(Status.REJECTED, name, result, result_issues)
