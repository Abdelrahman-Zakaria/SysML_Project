"""Milestone 3 - call budget + final-answer audit.

GuardedDispatcher  : dispatch() wrapped with a hard call budget and automatic
                     ledger recording.
audit_answer       : the only way to obtain Outcome.VERIFIED. It checks that an
                     answer is grounded in ledger facts.

What the audit checks is *grounding*: cited IDs exist, cited entries succeeded,
they came from the right kind of tool, and validity claims are bound to a
passing validate_candidate entry for the exact candidate fingerprint. It does
not try to interpret free-text; claims that matter most (VALID) carry
machine-checkable fields instead.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from .dispatcher import DispatchEnvelope, Status, _display_name, dispatch
from .ledger import Ledger, LedgerEntry
from .model import Model
from .registry import DEFAULT_REGISTRY, ToolContext, ToolRegistry
from .results import Issue, IssueCode


# --------------------------------------------------------------------------
# Call budget + automatic ledger recording
# --------------------------------------------------------------------------
class GuardedDispatcher:
    """Every call is budget-checked, dispatched, and recorded.

    Budget rules: every call that reaches the dispatcher consumes one unit,
    whatever its outcome (a rejected or crashing call still costs). Once
    calls_used == max_calls, further calls are blocked: the tool is NOT executed,
    the call is recorded as REJECTED/BUDGET_EXHAUSTED, and calls_used stays put.
    """

    def __init__(self, max_calls: int, registry: ToolRegistry = DEFAULT_REGISTRY,
                 ledger: Optional[Ledger] = None) -> None:
        if type(max_calls) is not int or max_calls < 0:
            raise ValueError("max_calls must be an int >= 0")
        self._max_calls = max_calls
        self._registry = registry
        self._ledger = ledger if ledger is not None else Ledger()
        self._used = 0
        self._blocked = 0

    @property
    def ledger(self) -> Ledger:
        return self._ledger

    @property
    def max_calls(self) -> int:
        return self._max_calls

    @property
    def calls_used(self) -> int:
        return self._used

    @property
    def calls_remaining(self) -> int:
        return self._max_calls - self._used

    @property
    def calls_blocked(self) -> int:
        return self._blocked

    def call(self, tool_name: object, raw_args: object, context: ToolContext) -> LedgerEntry:
        if self._used >= self._max_calls:
            self._blocked += 1
            envelope = DispatchEnvelope(
                Status.REJECTED, _display_name(tool_name), None,
                (Issue(IssueCode.BUDGET_EXHAUSTED,
                       f"Call budget exhausted: {self._used} of {self._max_calls} calls "
                       "used. No further tool calls are allowed."),))
            return self._ledger.record(envelope, raw_args)

        self._used += 1
        subject = self._subject_fingerprint(tool_name, context)
        envelope = dispatch(tool_name, raw_args, context, self._registry)
        return self._ledger.record(envelope, raw_args, subject)

    @staticmethod
    def _subject_fingerprint(tool_name: object, context: object) -> Optional[str]:
        if tool_name != "validate_candidate":
            return None
        candidate = getattr(context, "candidate", None)
        if not isinstance(candidate, Model):
            return None
        try:
            return candidate.fingerprint()
        except Exception:  # noqa: BLE001
            return None


# --------------------------------------------------------------------------
# Answer types
# --------------------------------------------------------------------------
class ClaimKind(str, Enum):
    FACT = "FACT"          # a statement about the model, grounded in inspect_model
    PROPOSAL = "PROPOSAL"  # "this change was proposed", grounded in propose_operation
    VALID = "VALID"        # "this candidate is valid", grounded in validate_candidate


@dataclass(frozen=True)
class Claim:
    kind: ClaimKind
    text: str
    evidence_ids: tuple = ()
    candidate_fingerprint: Optional[str] = None   # required for VALID


@dataclass(frozen=True)
class FinalAnswer:
    """A positive answer: every claim must be grounded."""

    summary: str
    claims: tuple = ()


@dataclass(frozen=True)
class NoEvidenceAnswer:
    """The honest alternative: 'I could not ground an answer.'"""

    reason: str
    evidence_ids: tuple = ()   # optional context; if given, must exist


class Outcome(str, Enum):
    VERIFIED = "VERIFIED"
    NO_EVIDENCE = "NO_EVIDENCE"
    REJECTED = "REJECTED"      # the answer failed the audit and must not be shown as a result


@dataclass(frozen=True)
class AuditResult:
    outcome: Outcome
    issues: tuple = ()
    cited_evidence_ids: tuple = ()

    def __post_init__(self) -> None:
        if not isinstance(self.outcome, Outcome):
            raise ValueError("outcome must be an Outcome member")
        if self.outcome is Outcome.REJECTED and not self.issues:
            raise ValueError("a REJECTED audit requires at least one issue")
        if self.outcome is not Outcome.REJECTED and self.issues:
            raise ValueError("only a REJECTED audit may carry issues")


_ALLOWED_TOOLS = {
    ClaimKind.FACT: frozenset({"inspect_model"}),
    ClaimKind.PROPOSAL: frozenset({"propose_operation"}),
    ClaimKind.VALID: frozenset({"propose_operation", "validate_candidate"}),
}


# --------------------------------------------------------------------------
# Audit
# --------------------------------------------------------------------------
def _rejected(*issues: Issue) -> AuditResult:
    return AuditResult(Outcome.REJECTED, tuple(issues))


def _ordered(ids) -> tuple:
    return tuple(sorted(set(ids), key=lambda s: int(s[3:])))   # "ev_12" -> 12


def _ids_issues(ids: object, ledger: Ledger, prefix: str) -> tuple:
    """Return (existing_entries, issues) for a tuple of cited IDs."""
    if not isinstance(ids, tuple) or any(type(i) is not str for i in ids):
        return [], [Issue(IssueCode.INVALID_ANSWER,
                          f"{prefix}evidence_ids must be a tuple of strings.")]
    entries, issues = [], []
    for eid in ids:
        entry = ledger.get(eid)
        if entry is None:
            issues.append(Issue(IssueCode.UNKNOWN_EVIDENCE_ID,
                                f"{prefix}evidence ID '{eid}' does not exist in the ledger.",
                                eid))
        else:
            entries.append(entry)
    return entries, issues


def _audit_claim(n: int, claim: object, ledger: Ledger) -> tuple:
    """Return (issues, existing_entries) for one claim."""
    prefix = f"claim {n}: "
    if not isinstance(claim, Claim):
        return [Issue(IssueCode.INVALID_ANSWER,
                      f"{prefix}must be a Claim, got {type(claim).__name__}.")], []
    if not isinstance(claim.kind, ClaimKind):
        return [Issue(IssueCode.INVALID_ANSWER, f"{prefix}unknown claim kind.")], []
    if type(claim.text) is not str or not claim.text.strip():
        return [Issue(IssueCode.INVALID_ANSWER, f"{prefix}text must be a non-empty string.")], []

    entries, issues = _ids_issues(claim.evidence_ids, ledger, prefix)
    if any(i.code == IssueCode.INVALID_ANSWER for i in issues):
        return issues, []
    if not claim.evidence_ids:
        issues.append(Issue(IssueCode.UNSUPPORTED_CLAIM,
                            f"{prefix}no evidence cited; every claim must cite ledger entries."))

    allowed = _ALLOWED_TOOLS[claim.kind]
    for e in entries:
        if e.status is not Status.OK:
            issues.append(Issue(
                IssueCode.CITES_FAILED_EVIDENCE,
                f"{prefix}{e.evidence_id} ({e.tool_name}) has status {e.status.value}; "
                "it cannot be cited as proof of success.", e.evidence_id))
        elif e.tool_name not in allowed:
            issues.append(Issue(
                IssueCode.WRONG_EVIDENCE_KIND,
                f"{prefix}{e.evidence_id} came from '{e.tool_name}', which cannot support "
                f"a {claim.kind.value} claim.", e.evidence_id))

    fp = claim.candidate_fingerprint
    if claim.kind is ClaimKind.VALID:
        if type(fp) is not str or not fp:
            issues.append(Issue(IssueCode.UNSUPPORTED_CLAIM,
                                f"{prefix}a VALID claim must name the candidate_fingerprint "
                                "it refers to."))
        else:
            passing = [e for e in entries
                       if e.tool_name == "validate_candidate" and e.status is Status.OK
                       and getattr(e.result, "passed", False) is True]
            if not passing:
                issues.append(Issue(
                    IssueCode.NOT_VALIDATED,
                    f"{prefix}no passing validate_candidate entry is cited, so the "
                    "candidate is not shown to be valid."))
            elif not any(e.candidate_fingerprint == fp and e.subject_fingerprint == fp
                         for e in passing):
                issues.append(Issue(
                    IssueCode.FINGERPRINT_MISMATCH,
                    f"{prefix}the cited passing validation does not match candidate "
                    f"fingerprint '{fp[:12]}...'."))
    elif claim.kind is ClaimKind.PROPOSAL and fp is not None:
        proposals = [e for e in entries if e.tool_name == "propose_operation"]
        if not any(e.candidate_fingerprint == fp for e in proposals):
            issues.append(Issue(
                IssueCode.FINGERPRINT_MISMATCH,
                f"{prefix}no cited proposal produced candidate fingerprint '{str(fp)[:12]}...'."))

    return issues, entries


def _audit_final(answer: FinalAnswer, ledger: Ledger) -> AuditResult:
    issues: list = []
    if type(answer.summary) is not str or not answer.summary.strip():
        issues.append(Issue(IssueCode.INVALID_ANSWER, "summary must be a non-empty string."))
    if not isinstance(answer.claims, tuple):
        return _rejected(*issues, Issue(IssueCode.INVALID_ANSWER, "claims must be a tuple."))
    if not answer.claims:
        issues.append(Issue(IssueCode.NO_CLAIMS,
                            "A FinalAnswer needs at least one grounded claim. "
                            "If nothing can be grounded, return a NoEvidenceAnswer."))
    cited: list = []
    for n, claim in enumerate(answer.claims, start=1):
        claim_issues, entries = _audit_claim(n, claim, ledger)
        issues.extend(claim_issues)
        cited.extend(e.evidence_id for e in entries)
    if issues:
        return _rejected(*issues)
    return AuditResult(Outcome.VERIFIED, (), _ordered(cited))


def _audit_no_evidence(answer: NoEvidenceAnswer, ledger: Ledger) -> AuditResult:
    issues: list = []
    if type(answer.reason) is not str or not answer.reason.strip():
        issues.append(Issue(IssueCode.INVALID_ANSWER,
                            "A NoEvidenceAnswer must state a non-empty reason."))
    entries, id_issues = _ids_issues(answer.evidence_ids, ledger, "")
    issues.extend(id_issues)
    if issues:
        return _rejected(*issues)
    return AuditResult(Outcome.NO_EVIDENCE, (), _ordered(e.evidence_id for e in entries))


def audit_answer(answer: object, ledger: Ledger) -> AuditResult:
    """Read-only. Never mutates the ledger."""
    if not isinstance(ledger, Ledger):
        raise TypeError("audit_answer requires a Ledger")
    if isinstance(answer, FinalAnswer):
        return _audit_final(answer, ledger)
    if isinstance(answer, NoEvidenceAnswer):
        return _audit_no_evidence(answer, ledger)
    return _rejected(Issue(
        IssueCode.INVALID_ANSWER,
        f"Answer must be FinalAnswer or NoEvidenceAnswer, got {type(answer).__name__}."))
