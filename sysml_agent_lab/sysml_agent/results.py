"""Milestone 1 - typed results returned by every tool.

Failures are ordinary, structured values (ok=False / passed=False plus Issues),
never exceptions and never empty "success" objects.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .model import Model


class IssueCode:
    # structural / validator rules
    DUPLICATE_ID = "DUPLICATE_ID"
    UNKNOWN_DOMAIN = "UNKNOWN_DOMAIN"
    MISSING_REQUIREMENT = "MISSING_REQUIREMENT"
    MISSING_PART = "MISSING_PART"
    WRONG_ELEMENT_TYPE = "WRONG_ELEMENT_TYPE"
    DOMAIN_MISMATCH = "DOMAIN_MISMATCH"
    DUPLICATE_SATISFY = "DUPLICATE_SATISFY"
    # tool-level rejections
    INVALID_INPUT = "INVALID_INPUT"
    TARGET_NOT_FOUND = "TARGET_NOT_FOUND"
    UNSUPPORTED_OPERATION = "UNSUPPORTED_OPERATION"
    EMPTY_NAME = "EMPTY_NAME"
    # dispatch-layer rejections and errors (Milestone 2)
    UNKNOWN_TOOL = "UNKNOWN_TOOL"
    INVALID_ARGUMENTS = "INVALID_ARGUMENTS"
    MISSING_ARGUMENT = "MISSING_ARGUMENT"
    UNEXPECTED_ARGUMENT = "UNEXPECTED_ARGUMENT"
    WRONG_TYPE = "WRONG_TYPE"
    EMPTY_VALUE = "EMPTY_VALUE"
    NO_CANDIDATE = "NO_CANDIDATE"
    TOOL_EXCEPTION = "TOOL_EXCEPTION"
    BAD_TOOL_RESULT = "BAD_TOOL_RESULT"
    UNEXPLAINED_FAILURE = "UNEXPLAINED_FAILURE"
    # guardrail codes (Milestone 3)
    BUDGET_EXHAUSTED = "BUDGET_EXHAUSTED"
    UNKNOWN_EVIDENCE_ID = "UNKNOWN_EVIDENCE_ID"
    CITES_FAILED_EVIDENCE = "CITES_FAILED_EVIDENCE"
    WRONG_EVIDENCE_KIND = "WRONG_EVIDENCE_KIND"
    UNSUPPORTED_CLAIM = "UNSUPPORTED_CLAIM"
    NOT_VALIDATED = "NOT_VALIDATED"
    FINGERPRINT_MISMATCH = "FINGERPRINT_MISMATCH"
    NO_CLAIMS = "NO_CLAIMS"
    INVALID_ANSWER = "INVALID_ANSWER"
    # agent-loop codes (Milestone 4)
    MALFORMED_TURN = "MALFORMED_TURN"
    LLM_ERROR = "LLM_ERROR"


@dataclass(frozen=True)
class Issue:
    code: str
    message: str
    element_id: Optional[str] = None


@dataclass(frozen=True)
class InspectResult:
    ok: bool
    model_name: str
    parts: tuple
    requirements: tuple
    satisfies: tuple
    unsatisfied_requirement_ids: tuple
    issues: tuple = ()


@dataclass(frozen=True)
class ProposalResult:
    """A candidate is only a *proposal*. Nothing here claims it is valid;
    only a ValidationResult can say that."""

    ok: bool
    operation: object
    candidate: Optional[Model]
    candidate_fingerprint: Optional[str]
    changes: tuple = ()
    issues: tuple = ()


@dataclass(frozen=True)
class ValidationResult:
    passed: bool
    candidate_fingerprint: Optional[str]
    rules_checked: tuple
    issues: tuple = ()
