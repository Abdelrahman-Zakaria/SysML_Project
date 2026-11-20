"""Milestone 2 - the tool whitelist. A tool that is not here does not exist."""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Callable, Optional

from .model import Model
from .results import InspectResult, ProposalResult, ValidationResult
from .schema import ArgSchema, FieldSpec, parse_operation
from .tools import inspect_model, propose_operation, validate_candidate

ALLOWED_TOOL_NAMES: frozenset = frozenset(
    {"inspect_model", "propose_operation", "validate_candidate"})


@dataclass(frozen=True)
class ToolContext:
    """Trusted, harness-owned state. The LLM never serializes or supplies these."""

    model: Optional[Model]
    candidate: Optional[Model] = None

    def with_candidate(self, candidate: Optional[Model]) -> "ToolContext":
        return replace(self, candidate=candidate)


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    schema: ArgSchema
    func: Callable                 # the deterministic tool
    result_type: type              # what func must return
    is_positive: Callable          # result -> bool (OK vs REJECTED)
    bind: Callable                 # (context, clean_args) -> positional args for func
    normalize: Optional[Callable] = None   # clean_args -> (args, issues), e.g. dict -> typed op
    needs_candidate: bool = False


def _normalize_propose(args: dict) -> tuple:
    op, issues = parse_operation(args["operation"])
    return ({}, issues) if issues else ({"operation": op}, ())


DEFAULT_TOOLS = (
    ToolSpec(
        name="inspect_model",
        description="Read exact facts from the active model; optionally for one element_id.",
        schema=ArgSchema((FieldSpec("element_id", str, required=False),)),
        func=inspect_model,
        result_type=InspectResult,
        is_positive=lambda r: r.ok,
        bind=lambda ctx, a: (ctx.model, a.get("element_id")),
    ),
    ToolSpec(
        name="propose_operation",
        description="Propose AddRequirement / AddSatisfy / RenameElement; returns a candidate copy.",
        schema=ArgSchema((FieldSpec("operation", dict),)),
        func=propose_operation,
        result_type=ProposalResult,
        is_positive=lambda r: r.ok,
        bind=lambda ctx, a: (ctx.model, a["operation"]),
        normalize=_normalize_propose,
    ),
    ToolSpec(
        name="validate_candidate",
        description="Validate the latest proposed candidate against structural and domain rules.",
        schema=ArgSchema(()),
        func=validate_candidate,
        result_type=ValidationResult,
        is_positive=lambda r: r.passed,
        bind=lambda ctx, a: (ctx.candidate,),
        needs_candidate=True,
    ),
)


@dataclass(frozen=True)
class ToolRegistry:
    tools: tuple

    def __post_init__(self) -> None:
        names = [t.name for t in self.tools]
        if len(set(names)) != len(names):
            raise ValueError("duplicate tool names in registry")
        rogue = sorted(set(names) - ALLOWED_TOOL_NAMES)
        if rogue:
            raise ValueError(f"tool names not on the whitelist: {rogue}")

    def get(self, name: object) -> Optional[ToolSpec]:
        for t in self.tools:
            if t.name == name:
                return t
        return None

    def names(self) -> tuple:
        return tuple(sorted(t.name for t in self.tools))


DEFAULT_REGISTRY = ToolRegistry(DEFAULT_TOOLS)
