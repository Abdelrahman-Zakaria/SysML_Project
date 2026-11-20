"""Milestone 3 - the append-only evidence ledger.

Every tool call that reaches the GuardedDispatcher (including rejected, failed
and budget-blocked ones) becomes one immutable LedgerEntry with a sequential ID
(ev_1, ev_2, ...). The ledger exposes no way to edit, reorder or delete entries
and does not let callers choose IDs. Only the harness-owned GuardedDispatcher
should call record(); the LLM never touches the ledger, it can only *cite* IDs.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Optional

from .dispatcher import DispatchEnvelope, Status


@dataclass(frozen=True)
class LedgerEntry:
    evidence_id: str
    tool_name: str
    arguments: object                 # deep-copied snapshot of the raw arguments
    status: Status
    result: Optional[object]          # the typed tool result, if the tool ran
    issues: tuple
    # What the tool's own result says it examined/produced (ProposalResult or
    # ValidationResult), or None.
    candidate_fingerprint: Optional[str] = None
    # What the *harness* knows was validated: the fingerprint of the context's
    # candidate at call time (validate_candidate only). Independent of the tool.
    subject_fingerprint: Optional[str] = None


def _snapshot(arguments: object) -> object:
    try:
        return copy.deepcopy(arguments)
    except Exception:  # noqa: BLE001 - never let logging crash a call
        return f"<unsnapshottable {type(arguments).__name__}>"


class Ledger:
    def __init__(self) -> None:
        self._entries: list = []
        self._by_id: dict = {}

    def __len__(self) -> int:
        return len(self._entries)

    @property
    def entries(self) -> tuple:
        """A copy; changing it cannot change the ledger."""
        return tuple(self._entries)

    def get(self, evidence_id: object) -> Optional[LedgerEntry]:
        if not isinstance(evidence_id, str):
            return None
        return self._by_id.get(evidence_id)

    def record(self, envelope: DispatchEnvelope, arguments: object,
               subject_fingerprint: Optional[str] = None) -> LedgerEntry:
        fp = getattr(envelope.result, "candidate_fingerprint", None)
        entry = LedgerEntry(
            evidence_id=f"ev_{len(self._entries) + 1}",
            tool_name=envelope.tool_name,
            arguments=_snapshot(arguments),
            status=envelope.status,
            result=envelope.result,
            issues=envelope.issues,
            candidate_fingerprint=fp if isinstance(fp, str) else None,
            subject_fingerprint=subject_fingerprint,
        )
        self._entries.append(entry)
        self._by_id[entry.evidence_id] = entry
        return entry
