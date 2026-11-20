"""Milestone 1 - the three deterministic tools. No LLM, no I/O, no randomness."""
from __future__ import annotations

from collections import Counter
from dataclasses import replace

from .model import VALID_DOMAINS, Model, Requirement, Satisfy
from .operations import AddRequirement, AddSatisfy, RenameElement
from .results import InspectResult, Issue, IssueCode, ProposalResult, ValidationResult

RULES_CHECKED = (
    "unique_ids",
    "known_domains",
    "satisfy_endpoints_exist",
    "satisfy_endpoint_types",
    "satisfy_domain_match",
    "unique_satisfy_links",
)


def _not_a_model(thing: object) -> Issue:
    return Issue(IssueCode.INVALID_INPUT,
                 f"Expected a Model instance, got {type(thing).__name__}.")


def _sorted(issues: list) -> tuple:
    return tuple(sorted(issues, key=lambda i: (i.element_id or "", i.code, i.message)))


# --------------------------------------------------------------------------
# Tool 1: inspect_model
# --------------------------------------------------------------------------
def inspect_model(model: Model, element_id: str = None) -> InspectResult:
    """Return exact facts from the model, or the facts about one element."""
    if not isinstance(model, Model):
        return InspectResult(False, "", (), (), (), (), (_not_a_model(model),))

    satisfied = {s.requirement_id for s in model.satisfies}

    if element_id is None:
        unsatisfied = tuple(r.id for r in model.requirements if r.id not in satisfied)
        return InspectResult(True, model.name, model.parts, model.requirements,
                             model.satisfies, unsatisfied)

    parts = tuple(p for p in model.parts if p.id == element_id)
    reqs = tuple(r for r in model.requirements if r.id == element_id)
    if not parts and not reqs:
        return InspectResult(
            False, model.name, (), (), (), (),
            (Issue(IssueCode.TARGET_NOT_FOUND,
                   f"No element with ID '{element_id}' exists in model '{model.name}'.",
                   element_id),))

    links = tuple(s for s in model.satisfies
                  if s.requirement_id == element_id or s.part_id == element_id)
    unsatisfied = tuple(r.id for r in reqs if r.id not in satisfied)
    return InspectResult(True, model.name, parts, reqs, links, unsatisfied)


# --------------------------------------------------------------------------
# Tool 2: propose_operation
# --------------------------------------------------------------------------
def _reject(operation: object, issue: Issue) -> ProposalResult:
    return ProposalResult(False, operation, None, None, (), (issue,))


def propose_operation(model: Model, operation: object) -> ProposalResult:
    """Apply a typed operation to a *copy* of the model.

    This tool only refuses operations it cannot apply at all (unsupported type,
    unknown rename target, blank name). Semantic problems such as duplicate IDs,
    dangling links or domain mismatches are deliberately left in the candidate
    so that validate_candidate is the single judge of correctness.
    """
    if not isinstance(model, Model):
        return _reject(operation, _not_a_model(model))

    if isinstance(operation, AddRequirement):
        req = Requirement(operation.id, operation.name, operation.text, operation.domain)
        candidate = replace(model, requirements=model.requirements + (req,))
        changes = (f"added requirement {req.id} ({req.domain})",)

    elif isinstance(operation, AddSatisfy):
        link = Satisfy(operation.requirement_id, operation.part_id)
        candidate = replace(model, satisfies=model.satisfies + (link,))
        changes = (f"added satisfy {link.requirement_id} -> {link.part_id}",)

    elif isinstance(operation, RenameElement):
        if not isinstance(operation.new_name, str) or not operation.new_name.strip():
            return _reject(operation, Issue(IssueCode.EMPTY_NAME,
                                            "new_name must be a non-empty string.",
                                            operation.element_id))
        if operation.element_id not in model.all_ids():
            return _reject(operation, Issue(
                IssueCode.TARGET_NOT_FOUND,
                f"Cannot rename: no element with ID '{operation.element_id}'.",
                operation.element_id))
        eid, new = operation.element_id, operation.new_name
        candidate = replace(
            model,
            parts=tuple(replace(p, name=new) if p.id == eid else p for p in model.parts),
            requirements=tuple(replace(r, name=new) if r.id == eid else r
                               for r in model.requirements),
        )
        changes = (f"renamed {eid} to '{new}'",)

    else:
        return _reject(operation, Issue(
            IssueCode.UNSUPPORTED_OPERATION,
            f"Unsupported operation type: {type(operation).__name__}. "
            "Supported: AddRequirement, AddSatisfy, RenameElement."))

    return ProposalResult(True, operation, candidate, candidate.fingerprint(), changes)


# --------------------------------------------------------------------------
# Tool 3: validate_candidate
# --------------------------------------------------------------------------
def validate_candidate(candidate: Model) -> ValidationResult:
    """Check structural and domain rules. Pass means: zero issues found."""
    if not isinstance(candidate, Model):
        return ValidationResult(False, None, (), (_not_a_model(candidate),))

    issues: list = []

    # Rule: element IDs are unique across parts AND requirements.
    for eid, n in Counter(candidate.all_ids()).items():
        if n > 1:
            issues.append(Issue(IssueCode.DUPLICATE_ID,
                                f"ID '{eid}' is used by {n} elements; IDs must be unique.",
                                eid))

    # Rule: every element uses a known domain.
    for el in candidate.parts + candidate.requirements:
        if el.domain not in VALID_DOMAINS:
            issues.append(Issue(
                IssueCode.UNKNOWN_DOMAIN,
                f"Element '{el.id}' has unknown domain '{el.domain}'. "
                f"Allowed: {sorted(VALID_DOMAINS)}.", el.id))

    parts_by_id: dict = {}
    for p in candidate.parts:
        parts_by_id.setdefault(p.id, p)
    reqs_by_id: dict = {}
    for r in candidate.requirements:
        reqs_by_id.setdefault(r.id, r)

    # Rules: satisfy links.
    seen: set = set()
    for s in candidate.satisfies:
        key = (s.requirement_id, s.part_id)
        if key in seen:
            issues.append(Issue(IssueCode.DUPLICATE_SATISFY,
                                f"Duplicate satisfy link {s.requirement_id} -> {s.part_id}.",
                                s.requirement_id))
            continue
        seen.add(key)

        req = reqs_by_id.get(s.requirement_id)
        part = parts_by_id.get(s.part_id)

        if req is None:
            if s.requirement_id in parts_by_id:
                issues.append(Issue(
                    IssueCode.WRONG_ELEMENT_TYPE,
                    f"'{s.requirement_id}' is a part, but the source of a satisfy "
                    "link must be a requirement.", s.requirement_id))
            else:
                issues.append(Issue(
                    IssueCode.MISSING_REQUIREMENT,
                    f"Satisfy link references requirement '{s.requirement_id}', "
                    "which does not exist.", s.requirement_id))
        if part is None:
            if s.part_id in reqs_by_id:
                issues.append(Issue(
                    IssueCode.WRONG_ELEMENT_TYPE,
                    f"'{s.part_id}' is a requirement, but the target of a satisfy "
                    "link must be a part.", s.part_id))
            else:
                issues.append(Issue(
                    IssueCode.MISSING_PART,
                    f"Satisfy link references part '{s.part_id}', which does not exist.",
                    s.part_id))
        if req is not None and part is not None and req.domain != part.domain:
            issues.append(Issue(
                IssueCode.DOMAIN_MISMATCH,
                f"Requirement '{req.id}' ({req.domain}) cannot be satisfied by part "
                f"'{part.id}' ({part.domain}).", req.id))

    ordered = _sorted(issues)
    return ValidationResult(not ordered, candidate.fingerprint(), RULES_CHECKED, ordered)
