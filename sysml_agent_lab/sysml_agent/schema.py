"""Milestone 2 - strict argument schemas for untrusted (LLM-supplied) input.

Schemas check *shape* only: required keys, no extra keys, exact types,
non-empty strings. Engineering meaning (duplicate IDs, domain clashes...) is
still decided by validate_candidate.
"""
from __future__ import annotations

from dataclasses import dataclass

from .operations import AddRequirement, AddSatisfy, RenameElement
from .results import Issue, IssueCode


@dataclass(frozen=True)
class FieldSpec:
    name: str
    expected_type: type = str
    required: bool = True


@dataclass(frozen=True)
class ArgSchema:
    fields: tuple = ()


def _sorted(issues: list) -> tuple:
    return tuple(sorted(issues, key=lambda i: (i.code, i.message)))


def validate_args(schema: ArgSchema, raw: object, where: str = "arguments") -> tuple:
    """Return (clean_args, issues). clean_args is {} whenever issues is non-empty."""
    if not isinstance(raw, dict):
        return {}, (Issue(IssueCode.INVALID_ARGUMENTS,
                          f"{where}: must be a JSON object, got {type(raw).__name__}."),)

    issues: list = []
    known = {f.name for f in schema.fields}

    for key in raw:
        if not isinstance(key, str) or key not in known:
            issues.append(Issue(IssueCode.UNEXPECTED_ARGUMENT,
                                f"{where}: unexpected key {key!r}. "
                                f"Allowed keys: {sorted(known) if known else 'none'}."))

    clean: dict = {}
    for f in schema.fields:
        if f.name not in raw:
            if f.required:
                issues.append(Issue(IssueCode.MISSING_ARGUMENT,
                                    f"{where}: missing required field '{f.name}'."))
            continue
        value = raw[f.name]
        if type(value) is not f.expected_type:  # exact match: bool is not int, etc.
            issues.append(Issue(IssueCode.WRONG_TYPE,
                                f"{where}: field '{f.name}' must be "
                                f"{f.expected_type.__name__}, got {type(value).__name__}."))
        elif f.expected_type is str and not value.strip():
            issues.append(Issue(IssueCode.EMPTY_VALUE,
                                f"{where}: field '{f.name}' must not be empty."))
        else:
            clean[f.name] = value

    if issues:
        return {}, _sorted(issues)
    return clean, ()


# Raw operation dict -> typed operation. The "type" key selects the entry.
OPERATION_SPECS: dict = {
    "AddRequirement": (AddRequirement, ArgSchema((
        FieldSpec("id"), FieldSpec("name"), FieldSpec("text"), FieldSpec("domain")))),
    "AddSatisfy": (AddSatisfy, ArgSchema((
        FieldSpec("requirement_id"), FieldSpec("part_id")))),
    "RenameElement": (RenameElement, ArgSchema((
        FieldSpec("element_id"), FieldSpec("new_name")))),
}


def parse_operation(raw_op: object) -> tuple:
    """Return (typed_operation_or_None, issues)."""
    if not isinstance(raw_op, dict):
        return None, (Issue(IssueCode.INVALID_ARGUMENTS,
                            f"operation: must be a JSON object, got {type(raw_op).__name__}."),)
    if "type" not in raw_op:
        return None, (Issue(IssueCode.MISSING_ARGUMENT,
                            "operation: missing required field 'type'. "
                            f"Supported: {sorted(OPERATION_SPECS)}."),)
    op_type = raw_op["type"]
    if type(op_type) is not str:
        return None, (Issue(IssueCode.WRONG_TYPE,
                            f"operation: field 'type' must be str, got {type(op_type).__name__}."),)
    if op_type not in OPERATION_SPECS:
        return None, (Issue(IssueCode.UNSUPPORTED_OPERATION,
                            f"operation: unsupported type {op_type!r}. "
                            f"Supported: {sorted(OPERATION_SPECS)}."),)

    cls, schema = OPERATION_SPECS[op_type]
    rest = {k: v for k, v in raw_op.items() if k != "type"}
    clean, issues = validate_args(schema, rest, where=f"operation {op_type}")
    if issues:
        return None, issues
    return cls(**clean), ()
