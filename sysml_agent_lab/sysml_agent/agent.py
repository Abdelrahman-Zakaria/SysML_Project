"""Milestone 4 - the agent loop and the LLM interface.

The LLM is untrusted. It sees only JSON-like messages and answers with one raw
action dict per turn. The loop validates that envelope, routes tool calls
through the GuardedDispatcher (budget + ledger), and sends every final answer
through audit_answer. The run can only end as VERIFIED, NO_EVIDENCE or FAILED,
and VERIFIED is unreachable unless the audit itself returned VERIFIED.
"""
from __future__ import annotations

import copy
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Optional, Protocol

from .dispatcher import Status
from .guardrails import (AuditResult, Claim, ClaimKind, FinalAnswer, GuardedDispatcher,
                         NoEvidenceAnswer, Outcome, audit_answer)
from .model import Model
from .registry import DEFAULT_REGISTRY, ToolContext, ToolRegistry
from .results import (InspectResult, Issue, IssueCode, ProposalResult, ValidationResult)
from .schema import OPERATION_SPECS


# --------------------------------------------------------------------------
# LLM interface + scripted fake
# --------------------------------------------------------------------------
class LLMClient(Protocol):
    def next_step(self, messages: list) -> dict:
        """Take the conversation so far, return ONE raw action dict."""
        ...


class ScriptExhausted(Exception):
    """The scripted fake ran out of steps."""


def _safe_copy(value: object) -> object:
    try:
        return copy.deepcopy(value)
    except Exception:  # noqa: BLE001
        return f"<uncopyable {type(value).__name__}>"


class ScriptedLLM:
    """Deterministic stand-in for a real model: replays a fixed script.

    Each script step is one of:
      * a dict (or any object, to simulate junk) -> returned as a copy
      * a callable(messages) -> step, so the fake can react to observations the
        way a real model would (e.g. copy a fingerprint out of a tool result)
      * an Exception instance -> raised, to simulate an LLM/API failure
    """

    def __init__(self, steps, repeat_last: bool = False) -> None:
        self._steps = tuple(_safe_copy(s) if not callable(s) else s for s in steps)
        self._repeat_last = repeat_last
        self._next = 0
        self.received: list = []     # a copy of the history passed on every call

    def next_step(self, messages: list) -> dict:
        self.received.append(copy.deepcopy(messages))
        if self._next < len(self._steps):
            step = self._steps[self._next]
            self._next += 1
        elif self._repeat_last and self._steps:
            step = self._steps[-1]
        else:
            raise ScriptExhausted("the script has no more steps")
        if isinstance(step, Exception):
            raise step
        return step(messages) if callable(step) else _safe_copy(step)


# --------------------------------------------------------------------------
# Turn envelope validation and answer conversion
# --------------------------------------------------------------------------
_TURN_SHAPES = {   # type -> (allowed keys besides "type", required keys)
    "tool_call": (frozenset({"tool", "args"}), frozenset({"tool"})),
    "final_answer": (frozenset({"summary", "claims"}), frozenset({"summary", "claims"})),
    "no_evidence": (frozenset({"reason", "evidence_ids"}), frozenset({"reason"})),
}
_CLAIM_KEYS = frozenset({"kind", "text", "evidence_ids", "candidate_fingerprint"})


def check_turn(raw: object) -> tuple:
    """Validate only the outer envelope of a turn. Returns issues (empty = fine)."""
    if not isinstance(raw, dict):
        return (Issue(IssueCode.MALFORMED_TURN,
                      f"Turn must be a JSON object, got {type(raw).__name__}."),)
    turn_type = raw.get("type")
    if type(turn_type) is not str or turn_type not in _TURN_SHAPES:
        return (Issue(IssueCode.MALFORMED_TURN,
                      f"Turn 'type' must be one of {sorted(_TURN_SHAPES)}."),)
    allowed, required = _TURN_SHAPES[turn_type]
    issues = [Issue(IssueCode.MALFORMED_TURN, f"{turn_type}: unexpected key {key!r}.")
              for key in sorted((k for k in raw if k != "type" and k not in allowed), key=repr)]
    issues += [Issue(IssueCode.MALFORMED_TURN, f"{turn_type}: missing required key '{key}'.")
               for key in sorted(required - set(raw))]
    return tuple(issues)


def _claim_from_raw(raw: object) -> object:
    # Junk is passed through unchanged so audit_answer, the single judge, rejects it.
    if not isinstance(raw, dict) or not {"kind", "text"} <= set(raw) or not set(raw) <= _CLAIM_KEYS:
        return raw
    kind = raw["kind"]
    if type(kind) is str and kind in ClaimKind.__members__:
        kind = ClaimKind[kind]
    ids = raw.get("evidence_ids", ())
    if isinstance(ids, list):
        ids = tuple(ids)
    return Claim(kind, raw["text"], ids, raw.get("candidate_fingerprint"))


def answer_from_turn(raw: dict) -> object:
    """Convert a (envelope-valid) final_answer / no_evidence turn into answer objects."""
    if raw["type"] == "no_evidence":
        ids = raw.get("evidence_ids", ())
        return NoEvidenceAnswer(raw["reason"], tuple(ids) if isinstance(ids, list) else ids)
    claims = raw["claims"]
    if isinstance(claims, list):
        claims = tuple(_claim_from_raw(c) for c in claims)
    return FinalAnswer(raw["summary"], claims)


# --------------------------------------------------------------------------
# Observations (what the LLM is told about a tool call): JSON-like only
# --------------------------------------------------------------------------
def _issue_dicts(issues) -> list:
    return [{"code": i.code, "message": i.message, "element_id": i.element_id} for i in issues]


def _summarize_result(result: object) -> Optional[dict]:
    """A compact JSON view of a typed result. The full Model is never sent."""
    if isinstance(result, InspectResult):
        return {"ok": result.ok, "model_name": result.model_name,
                "parts": [asdict(p) for p in result.parts],
                "requirements": [asdict(r) for r in result.requirements],
                "satisfies": [asdict(s) for s in result.satisfies],
                "unsatisfied_requirement_ids": list(result.unsatisfied_requirement_ids)}
    if isinstance(result, ProposalResult):
        return {"ok": result.ok, "changes": list(result.changes),
                "candidate_fingerprint": result.candidate_fingerprint}
    if isinstance(result, ValidationResult):
        return {"passed": result.passed, "rules_checked": list(result.rules_checked),
                "candidate_fingerprint": result.candidate_fingerprint}
    return None


def _observation(entry, guarded: GuardedDispatcher) -> dict:
    return {"evidence_id": entry.evidence_id, "tool": entry.tool_name,
            "status": entry.status.value, "result": _summarize_result(entry.result),
            "issues": _issue_dicts(entry.issues),
            "candidate_fingerprint": entry.candidate_fingerprint,
            "calls_remaining": guarded.calls_remaining}


def _describe_schema(schema) -> str:
    if not schema.fields:
        return "none"
    return ", ".join(f"{f.name} ({f.expected_type.__name__}{'' if f.required else ', optional'})"
                     for f in schema.fields)


def build_system_prompt(registry: ToolRegistry = DEFAULT_REGISTRY) -> str:
    lines = [
        "You are an engineering assistant for a SysML v2 model. You act ONLY by replying with "
        "ONE JSON object per turn, in one of these shapes:",
        '  {"type": "tool_call", "tool": <tool name>, "args": {...}}',
        '  {"type": "final_answer", "summary": <str>, "claims": [{"kind": "FACT|PROPOSAL|VALID", '
        '"text": <str>, "evidence_ids": ["ev_1"], "candidate_fingerprint": <str, required for VALID>}]}',
        '  {"type": "no_evidence", "reason": <str>, "evidence_ids": [optional]}',
        "",
        "Rules: every claim must cite evidence IDs (ev_N) taken from tool observations. A tool "
        "result with status REJECTED or TOOL_ERROR proves nothing. A VALID claim needs a "
        "validate_candidate observation with status OK and passed=true, and you must copy that "
        "observation's candidate_fingerprint. If you cannot ground an answer, reply with "
        "no_evidence. Each proposal is applied to the original model, not stacked.",
        "",
        "Tools:",
    ]
    for spec in sorted(registry.tools, key=lambda t: t.name):
        lines.append(f"- {spec.name}: {spec.description} Arguments: {_describe_schema(spec.schema)}")
    lines.append("")
    lines.append('propose_operation "operation" is an object whose "type" is one of:')
    for name in sorted(OPERATION_SPECS):
        lines.append(f"- {name}: {_describe_schema(OPERATION_SPECS[name][1])}")
    return "\n".join(lines)


# --------------------------------------------------------------------------
# Run result
# --------------------------------------------------------------------------
class AgentStatus(str, Enum):
    VERIFIED = "VERIFIED"
    NO_EVIDENCE = "NO_EVIDENCE"
    FAILED = "FAILED"


class FailureReason(str, Enum):
    BUDGET_EXHAUSTED = "BUDGET_EXHAUSTED"
    ANSWER_REJECTED = "ANSWER_REJECTED"
    LLM_ERROR = "LLM_ERROR"
    TOO_MANY_MALFORMED_TURNS = "TOO_MANY_MALFORMED_TURNS"


@dataclass(frozen=True)
class AgentRunResult:
    status: AgentStatus
    answer: Optional[object] = None          # only ever an *audited, accepted* answer
    audit: Optional[AuditResult] = None
    failure_reason: Optional[FailureReason] = None
    issues: tuple = ()
    evidence: tuple = ()                     # the ledger entries
    messages: tuple = ()                     # the transcript
    calls_used: int = 0
    turns: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.status, AgentStatus):
            raise ValueError("status must be an AgentStatus member")
        if self.status is AgentStatus.VERIFIED:
            ok = (isinstance(self.answer, FinalAnswer) and isinstance(self.audit, AuditResult)
                  and self.audit.outcome is Outcome.VERIFIED)
        elif self.status is AgentStatus.NO_EVIDENCE:
            ok = (isinstance(self.answer, NoEvidenceAnswer) and isinstance(self.audit, AuditResult)
                  and self.audit.outcome is Outcome.NO_EVIDENCE)
        else:
            ok = (self.answer is None and isinstance(self.failure_reason, FailureReason)
                  and bool(self.issues))
        if self.status is not AgentStatus.FAILED:
            ok = ok and self.failure_reason is None and not self.issues
        if not ok:
            raise ValueError(f"inconsistent AgentRunResult for status {self.status.value}")

    @property
    def verified(self) -> bool:
        return self.status is AgentStatus.VERIFIED


# --------------------------------------------------------------------------
# The loop
# --------------------------------------------------------------------------
def run_agent(llm: LLMClient, task: str, model: Model, max_calls: int = 8, *,
              registry: ToolRegistry = DEFAULT_REGISTRY,
              max_malformed_turns: int = 3,
              max_answer_attempts: int = 1) -> AgentRunResult:
    """Run one task. Always terminates: every turn is a tool call (bounded by the
    budget), a malformed turn (bounded by max_malformed_turns) or an answer
    (bounded by max_answer_attempts when rejected)."""
    if type(task) is not str or not task.strip():
        raise ValueError("task must be a non-empty string")
    if type(max_malformed_turns) is not int or max_malformed_turns < 0:
        raise ValueError("max_malformed_turns must be an int >= 0")
    if type(max_answer_attempts) is not int or max_answer_attempts < 1:
        raise ValueError("max_answer_attempts must be an int >= 1")

    guarded = GuardedDispatcher(max_calls, registry)
    context = ToolContext(model=model)
    messages: list = [{"role": "system", "content": build_system_prompt(registry)},
                      {"role": "user", "content": task}]
    turns = malformed = rejected_answers = 0

    def fail(reason: FailureReason, issues, audit: Optional[AuditResult] = None) -> AgentRunResult:
        return AgentRunResult(AgentStatus.FAILED, None, audit, reason, tuple(issues),
                              guarded.ledger.entries, tuple(copy.deepcopy(messages)),
                              guarded.calls_used, turns)

    while True:
        turns += 1
        try:
            raw = llm.next_step(copy.deepcopy(messages))   # the LLM gets a copy, never our list
        except Exception as exc:  # noqa: BLE001 - an LLM/API failure is a FAILED run, not a crash
            return fail(FailureReason.LLM_ERROR, (Issue(
                IssueCode.LLM_ERROR, f"LLM raised {type(exc).__name__}: {str(exc)[:200]}"),))
        messages.append({"role": "assistant", "content": _safe_copy(raw)})

        # 1. outer envelope
        problems = check_turn(raw)
        if problems:
            malformed += 1
            messages.append({"role": "tool", "content": {
                "status": "MALFORMED_TURN", "issues": _issue_dicts(problems),
                "calls_remaining": guarded.calls_remaining}})
            if malformed > max_malformed_turns:
                return fail(FailureReason.TOO_MANY_MALFORMED_TURNS, problems)
            continue

        # 2. tool call
        if raw["type"] == "tool_call":
            entry = guarded.call(raw["tool"], raw.get("args", {}), context)
            if (entry.tool_name == "propose_operation" and entry.status is Status.OK
                    and isinstance(entry.result, ProposalResult)
                    and entry.result.candidate is not None):
                context = context.with_candidate(entry.result.candidate)
            messages.append({"role": "tool", "content": _observation(entry, guarded)})
            if any(i.code == IssueCode.BUDGET_EXHAUSTED for i in entry.issues):
                return fail(FailureReason.BUDGET_EXHAUSTED, entry.issues)
            continue

        # 3. final_answer / no_evidence -> audit decides, nothing else
        answer = answer_from_turn(raw)
        audit = audit_answer(answer, guarded.ledger)
        if audit.outcome is Outcome.REJECTED:
            rejected_answers += 1
            messages.append({"role": "tool", "content": {
                "status": "ANSWER_REJECTED", "issues": _issue_dicts(audit.issues),
                "attempts_remaining": max_answer_attempts - rejected_answers}})
            if rejected_answers >= max_answer_attempts:
                return fail(FailureReason.ANSWER_REJECTED, audit.issues, audit)
            continue

        status = (AgentStatus.VERIFIED if audit.outcome is Outcome.VERIFIED
                  else AgentStatus.NO_EVIDENCE)
        return AgentRunResult(status, answer, audit, None, (),
                              guarded.ledger.entries, tuple(copy.deepcopy(messages)),
                              guarded.calls_used, turns)
