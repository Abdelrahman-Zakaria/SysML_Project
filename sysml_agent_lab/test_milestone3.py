"""Milestone 3 tests: ledger, call budget, and final-answer audit.

Runs with either:  python -m unittest -v     or     pytest -v
"""
import unittest
from dataclasses import FrozenInstanceError, replace

from sysml_agent import (
    DEFAULT_REGISTRY, RULES_CHECKED, AuditResult, Claim, ClaimKind, FinalAnswer,
    GuardedDispatcher, InspectResult, IssueCode, Ledger, NoEvidenceAnswer, Outcome,
    ProposalResult, Status, ToolContext, ToolRegistry, ValidationResult,
    audit_answer, build_mock_model, inspect_model,
)

BASE = ToolContext(model=build_mock_model())
GOOD_OP = {"operation": {"type": "AddSatisfy", "requirement_id": "R-005", "part_id": "P-NAV"}}
BAD_OP = {"operation": {"type": "AddSatisfy", "requirement_id": "R-005", "part_id": "P-BAT"}}


def registry_with(name: str, **overrides) -> ToolRegistry:
    return ToolRegistry(tuple(replace(t, **overrides) if t.name == name else t
                              for t in DEFAULT_REGISTRY.tools))


def codes(result) -> set:
    return {i.code for i in result.issues}


def flow(gd: GuardedDispatcher, op: dict = GOOD_OP):
    """inspect -> propose -> validate. Returns the three ledger entries."""
    e_inspect = gd.call("inspect_model", {}, BASE)
    e_prop = gd.call("propose_operation", op, BASE)
    candidate = e_prop.result.candidate
    e_val = gd.call("validate_candidate", {}, BASE.with_candidate(candidate))
    return e_inspect, e_prop, e_val


def valid_claim(e_prop, e_val, fp=None):
    return Claim(ClaimKind.VALID, "The proposed change is valid.",
                 (e_prop.evidence_id, e_val.evidence_id),
                 fp if fp is not None else e_prop.candidate_fingerprint)


class LedgerTests(unittest.TestCase):
    def test_sequential_ids_and_recorded_fields(self):
        gd = GuardedDispatcher(max_calls=10)
        e1, e2, e3 = flow(gd)
        self.assertEqual([e.evidence_id for e in gd.ledger.entries], ["ev_1", "ev_2", "ev_3"])
        self.assertEqual((e1.tool_name, e2.tool_name, e3.tool_name),
                         ("inspect_model", "propose_operation", "validate_candidate"))
        self.assertEqual([e.status for e in (e1, e2, e3)], [Status.OK] * 3)
        self.assertEqual(e2.arguments, GOOD_OP)
        self.assertIsInstance(e1.result, InspectResult)
        self.assertIsInstance(e2.result, ProposalResult)
        self.assertIsInstance(e3.result, ValidationResult)

    def test_fingerprints_recorded(self):
        gd = GuardedDispatcher(max_calls=10)
        e1, e2, e3 = flow(gd)
        self.assertIsNone(e1.candidate_fingerprint)
        self.assertEqual(e2.candidate_fingerprint, e2.result.candidate.fingerprint())
        self.assertEqual(e3.candidate_fingerprint, e2.candidate_fingerprint)
        # harness-side fingerprint of what was actually validated, independent of the tool
        self.assertEqual(e3.subject_fingerprint, e2.candidate_fingerprint)
        self.assertIsNone(e1.subject_fingerprint)
        self.assertIsNone(e2.subject_fingerprint)

    def test_every_outcome_is_recorded(self):
        def crash(*_a):
            raise RuntimeError("boom")
        gd = GuardedDispatcher(10, registry_with("inspect_model", func=crash))
        entries = [
            gd.call("inspect_model", {}, BASE),                      # TOOL_ERROR
            gd.call("delete_model", {}, BASE),                       # REJECTED unknown tool
            gd.call("propose_operation", {}, BASE),                  # REJECTED bad args
            gd.call("validate_candidate", {}, BASE),                 # REJECTED no candidate
        ]
        self.assertEqual([e.status for e in entries],
                         [Status.TOOL_ERROR, Status.REJECTED, Status.REJECTED, Status.REJECTED])
        self.assertEqual(len(gd.ledger), 4)
        self.assertTrue(all(e.issues for e in entries))

    def test_arguments_are_snapshotted(self):
        gd = GuardedDispatcher(5)
        args = {"element_id": "R-001"}
        entry = gd.call("inspect_model", args, BASE)
        args["element_id"] = "TAMPERED"
        self.assertEqual(entry.arguments, {"element_id": "R-001"})

    def test_ledger_is_append_only(self):
        gd = GuardedDispatcher(5)
        entry = gd.call("inspect_model", {}, BASE)
        snapshot = gd.ledger.entries
        self.assertIsInstance(snapshot, tuple)
        with self.assertRaises(FrozenInstanceError):
            entry.status = Status.REJECTED
        gd.call("inspect_model", {}, BASE)
        self.assertEqual(len(snapshot), 1)               # old snapshot unaffected
        self.assertEqual(len(gd.ledger), 2)
        self.assertIs(gd.ledger.get("ev_1"), entry)
        for forbidden in ("delete", "remove", "clear", "pop", "update", "replace"):
            self.assertFalse(hasattr(gd.ledger, forbidden), forbidden)

    def test_get_is_safe_for_junk_ids(self):
        gd = GuardedDispatcher(5)
        gd.call("inspect_model", {}, BASE)
        for junk in ("ev_0", "ev_2", "EV_1", "ev_01", "", None, 1, ["ev_1"]):
            self.assertIsNone(gd.ledger.get(junk), junk)


class BudgetTests(unittest.TestCase):
    def test_over_budget_call_is_blocked_without_executing_the_tool(self):
        executed = []

        def counting(model, element_id=None):
            executed.append(element_id)
            return inspect_model(model, element_id)

        gd = GuardedDispatcher(2, registry_with("inspect_model", func=counting))
        self.assertEqual(gd.call("inspect_model", {}, BASE).status, Status.OK)
        self.assertEqual(gd.call("inspect_model", {}, BASE).status, Status.OK)
        self.assertEqual(gd.calls_remaining, 0)

        blocked = gd.call("inspect_model", {}, BASE)
        self.assertEqual(blocked.status, Status.REJECTED)
        self.assertEqual(codes(blocked), {IssueCode.BUDGET_EXHAUSTED})
        self.assertIsNone(blocked.result)
        self.assertEqual(len(executed), 2)               # tool body did not run again
        self.assertEqual(gd.calls_used, 2)
        self.assertEqual(gd.calls_blocked, 1)
        self.assertEqual(len(gd.ledger), 3)              # the attempt is still on record

    def test_blocking_applies_to_every_tool_and_to_junk_names(self):
        gd = GuardedDispatcher(1)
        gd.call("inspect_model", {}, BASE)
        for name in ("inspect_model", "propose_operation", "validate_candidate",
                     "delete_model", None, 5):
            e = gd.call(name, GOOD_OP, BASE)
            self.assertEqual(codes(e), {IssueCode.BUDGET_EXHAUSTED}, name)
        self.assertEqual(gd.calls_used, 1)

    def test_rejected_and_failed_calls_still_consume_budget(self):
        gd = GuardedDispatcher(3)
        gd.call("delete_model", {}, BASE)
        gd.call("inspect_model", {"bogus": 1}, BASE)
        gd.call("validate_candidate", {}, BASE)
        self.assertEqual(gd.calls_used, 3)
        self.assertEqual(codes(gd.call("inspect_model", {}, BASE)), {IssueCode.BUDGET_EXHAUSTED})

    def test_zero_budget_blocks_the_first_call(self):
        gd = GuardedDispatcher(0)
        self.assertEqual(codes(gd.call("inspect_model", {}, BASE)), {IssueCode.BUDGET_EXHAUSTED})
        self.assertEqual(gd.calls_used, 0)

    def test_invalid_budget_values_are_refused(self):
        for bad in (-1, "3", True, None, 2.5):
            with self.assertRaises(ValueError, msg=repr(bad)):
                GuardedDispatcher(bad)

    def test_counters(self):
        gd = GuardedDispatcher(4)
        self.assertEqual((gd.max_calls, gd.calls_used, gd.calls_remaining), (4, 0, 4))
        gd.call("inspect_model", {}, BASE)
        self.assertEqual((gd.calls_used, gd.calls_remaining), (1, 3))

    def test_a_blocked_entry_can_never_support_a_claim(self):
        gd = GuardedDispatcher(1)
        gd.call("inspect_model", {}, BASE)
        blocked = gd.call("inspect_model", {}, BASE)
        answer = FinalAnswer("x", (Claim(ClaimKind.FACT, "rover facts", (blocked.evidence_id,)),))
        self.assertEqual(audit_answer(answer, gd.ledger).outcome, Outcome.REJECTED)


class GroundedAnswerTests(unittest.TestCase):
    def setUp(self):
        self.gd = GuardedDispatcher(10)
        self.e_inspect, self.e_prop, self.e_val = flow(self.gd)

    def test_fully_grounded_answer_is_verified(self):
        answer = FinalAnswer("R-005 can be satisfied by P-NAV.", (
            Claim(ClaimKind.FACT, "R-005 is currently unsatisfied.", (self.e_inspect.evidence_id,)),
            Claim(ClaimKind.PROPOSAL, "AddSatisfy R-005 -> P-NAV was proposed.",
                  (self.e_prop.evidence_id,), self.e_prop.candidate_fingerprint),
            valid_claim(self.e_prop, self.e_val),
        ))
        result = audit_answer(answer, self.gd.ledger)
        self.assertEqual(result.outcome, Outcome.VERIFIED)
        self.assertEqual(result.issues, ())
        self.assertEqual(result.cited_evidence_ids, ("ev_1", "ev_2", "ev_3"))

    def test_valid_claim_with_only_the_validation_entry_is_enough(self):
        claim = Claim(ClaimKind.VALID, "valid", (self.e_val.evidence_id,),
                      self.e_val.subject_fingerprint)
        self.assertEqual(audit_answer(FinalAnswer("ok", (claim,)), self.gd.ledger).outcome,
                         Outcome.VERIFIED)

    def test_audit_is_deterministic_and_read_only(self):
        answer = FinalAnswer("ok", (valid_claim(self.e_prop, self.e_val),))
        before = self.gd.ledger.entries
        self.assertEqual(audit_answer(answer, self.gd.ledger), audit_answer(answer, self.gd.ledger))
        self.assertEqual(self.gd.ledger.entries, before)


class NoEvidenceTests(unittest.TestCase):
    def test_no_evidence_outcome(self):
        gd = GuardedDispatcher(3)
        r = audit_answer(NoEvidenceAnswer("No tool result establishes this."), gd.ledger)
        self.assertEqual(r.outcome, Outcome.NO_EVIDENCE)
        self.assertEqual(r.issues, ())

    def test_no_evidence_may_cite_real_entries_for_context(self):
        gd = GuardedDispatcher(5)
        _, _, e_val = flow(gd, BAD_OP)       # failed validation; honest to cite it
        r = audit_answer(NoEvidenceAnswer("Validation failed.", (e_val.evidence_id,)), gd.ledger)
        self.assertEqual(r.outcome, Outcome.NO_EVIDENCE)
        self.assertEqual(r.cited_evidence_ids, ("ev_3",))

    def test_no_evidence_still_rejects_fabricated_ids_and_empty_reasons(self):
        gd = GuardedDispatcher(3)
        r = audit_answer(NoEvidenceAnswer("because", ("ev_99",)), gd.ledger)
        self.assertEqual(r.outcome, Outcome.REJECTED)
        self.assertEqual(codes(r), {IssueCode.UNKNOWN_EVIDENCE_ID})
        for reason in ("", "   ", None, 5):
            r = audit_answer(NoEvidenceAnswer(reason), gd.ledger)
            self.assertEqual(r.outcome, Outcome.REJECTED, reason)


class RejectedAnswerTests(unittest.TestCase):
    def audit(self, gd, *claims, summary="done"):
        return audit_answer(FinalAnswer(summary, tuple(claims)), gd.ledger)

    def assert_rejected(self, result, *expected):
        self.assertEqual(result.outcome, Outcome.REJECTED)
        self.assertTrue(set(expected) <= codes(result), (expected, codes(result)))
        self.assertTrue(all(i.message.strip() for i in result.issues))

    def test_fabricated_evidence_ids(self):
        gd = GuardedDispatcher(5)
        flow(gd)
        for fake in ("ev_99", "ev_0", "ev_01", "EV_1", "ev_", "", "1"):
            r = self.audit(gd, Claim(ClaimKind.FACT, "facts", (fake,)))
            self.assert_rejected(r, IssueCode.UNKNOWN_EVIDENCE_ID)

    def test_non_string_evidence_ids_and_non_tuple(self):
        gd = GuardedDispatcher(5)
        flow(gd)
        self.assert_rejected(self.audit(gd, Claim(ClaimKind.FACT, "f", (1,))),
                             IssueCode.INVALID_ANSWER)
        self.assert_rejected(self.audit(gd, Claim(ClaimKind.FACT, "f", ["ev_1"])),
                             IssueCode.INVALID_ANSWER)

    def test_claim_without_evidence(self):
        gd = GuardedDispatcher(5)
        flow(gd)
        self.assert_rejected(self.audit(gd, Claim(ClaimKind.FACT, "trust me", ())),
                             IssueCode.UNSUPPORTED_CLAIM)

    def test_cannot_cite_a_rejected_entry_as_success(self):
        gd = GuardedDispatcher(5)
        bad = gd.call("inspect_model", {"element_id": "R-404"}, BASE)
        self.assertEqual(bad.status, Status.REJECTED)
        self.assert_rejected(self.audit(gd, Claim(ClaimKind.FACT, "R-404 exists", (bad.evidence_id,))),
                             IssueCode.CITES_FAILED_EVIDENCE)

    def test_cannot_cite_a_tool_error_entry_as_success(self):
        def crash(*_a):
            raise RuntimeError("boom")
        gd = GuardedDispatcher(5, registry_with("inspect_model", func=crash))
        err = gd.call("inspect_model", {}, BASE)
        self.assertEqual(err.status, Status.TOOL_ERROR)
        self.assert_rejected(self.audit(gd, Claim(ClaimKind.FACT, "model facts", (err.evidence_id,))),
                             IssueCode.CITES_FAILED_EVIDENCE)

    def test_valid_claim_without_any_validation(self):
        gd = GuardedDispatcher(5)
        gd.call("inspect_model", {}, BASE)
        e_prop = gd.call("propose_operation", GOOD_OP, BASE)
        claim = Claim(ClaimKind.VALID, "valid", (e_prop.evidence_id,), e_prop.candidate_fingerprint)
        self.assert_rejected(self.audit(gd, claim), IssueCode.NOT_VALIDATED)

    def test_valid_claim_that_cites_nothing(self):
        gd = GuardedDispatcher(5)
        _, e_prop, _ = flow(gd)     # a passing validation exists, but the claim doesn't cite it
        claim = Claim(ClaimKind.VALID, "valid", (), e_prop.candidate_fingerprint)
        self.assert_rejected(self.audit(gd, claim), IssueCode.UNSUPPORTED_CLAIM)

    def test_valid_claim_must_name_a_fingerprint(self):
        gd = GuardedDispatcher(5)
        _, e_prop, e_val = flow(gd)
        for fp in (None, "", 7):
            claim = Claim(ClaimKind.VALID, "valid", (e_prop.evidence_id, e_val.evidence_id), fp)
            self.assert_rejected(self.audit(gd, claim), IssueCode.UNSUPPORTED_CLAIM)

    def test_valid_claim_after_a_failed_validation(self):
        gd = GuardedDispatcher(5)
        _, e_prop, e_val = flow(gd, BAD_OP)      # domain mismatch -> validation REJECTED
        self.assertEqual(e_val.status, Status.REJECTED)
        self.assertEqual(codes(e_val), {IssueCode.DOMAIN_MISMATCH})
        r = self.audit(gd, valid_claim(e_prop, e_val))
        self.assert_rejected(r, IssueCode.CITES_FAILED_EVIDENCE, IssueCode.NOT_VALIDATED)
        self.assertNotEqual(r.outcome, Outcome.VERIFIED)

    def test_valid_claim_for_a_different_candidate(self):
        gd = GuardedDispatcher(10)
        _, e_prop, e_val = flow(gd)                      # candidate A passes
        for other_fp in (build_mock_model().fingerprint(), "0" * 64):
            claim = valid_claim(e_prop, e_val, fp=other_fp)
            self.assert_rejected(self.audit(gd, claim), IssueCode.FINGERPRINT_MISMATCH)

    def test_passing_validation_of_a_different_candidate_does_not_transfer(self):
        gd = GuardedDispatcher(10)
        _, _, val_good = flow(gd)                        # candidate A (valid)
        e_prop_b = gd.call("propose_operation", BAD_OP, BASE)   # candidate B (invalid), never validated
        claim = Claim(ClaimKind.VALID, "B is valid", (val_good.evidence_id,),
                      e_prop_b.candidate_fingerprint)
        self.assert_rejected(self.audit(gd, claim), IssueCode.FINGERPRINT_MISMATCH)

    def test_lying_validator_fingerprint_is_caught_by_harness_side_fingerprint(self):
        other_fp = build_mock_model().fingerprint()
        liar = lambda candidate: ValidationResult(True, other_fp, RULES_CHECKED, ())  # noqa: E731
        gd = GuardedDispatcher(10, registry_with("validate_candidate", func=liar))
        _, e_prop, e_val = flow(gd)
        self.assertEqual(e_val.status, Status.OK)        # the lie got through dispatch...
        cand_fp = e_prop.candidate_fingerprint
        for fp in (cand_fp, other_fp):                   # ...but cannot satisfy the audit
            r = self.audit(gd, valid_claim(e_prop, e_val, fp=fp))
            self.assert_rejected(r, IssueCode.FINGERPRINT_MISMATCH)

    def test_evidence_from_the_wrong_kind_of_tool(self):
        gd = GuardedDispatcher(5)
        e_inspect, e_prop, _ = flow(gd)
        self.assert_rejected(self.audit(gd, Claim(ClaimKind.FACT, "f", (e_prop.evidence_id,))),
                             IssueCode.WRONG_EVIDENCE_KIND)
        self.assert_rejected(self.audit(gd, Claim(ClaimKind.PROPOSAL, "p", (e_inspect.evidence_id,))),
                             IssueCode.WRONG_EVIDENCE_KIND)

    def test_proposal_fingerprint_must_match_a_cited_proposal(self):
        gd = GuardedDispatcher(5)
        _, e_prop, _ = flow(gd)
        claim = Claim(ClaimKind.PROPOSAL, "p", (e_prop.evidence_id,), "f" * 64)
        self.assert_rejected(self.audit(gd, claim), IssueCode.FINGERPRINT_MISMATCH)

    def test_one_bad_claim_rejects_the_whole_answer(self):
        gd = GuardedDispatcher(5)
        e_inspect, _, _ = flow(gd)
        good = Claim(ClaimKind.FACT, "fact", (e_inspect.evidence_id,))
        bad = Claim(ClaimKind.FACT, "invented", ("ev_77",))
        r = self.audit(gd, good, bad)
        self.assert_rejected(r, IssueCode.UNKNOWN_EVIDENCE_ID)
        self.assertIn("claim 2", r.issues[0].message)

    def test_all_problems_are_reported_together(self):
        gd = GuardedDispatcher(5)
        flow(gd)
        r = self.audit(gd, Claim(ClaimKind.FACT, "a", ()), Claim(ClaimKind.FACT, "b", ("ev_42",)))
        self.assertEqual(codes(r), {IssueCode.UNSUPPORTED_CLAIM, IssueCode.UNKNOWN_EVIDENCE_ID})

    def test_answers_with_no_claims_or_the_wrong_shape(self):
        gd = GuardedDispatcher(5)
        flow(gd)
        self.assert_rejected(audit_answer(FinalAnswer("done", ()), gd.ledger), IssueCode.NO_CLAIMS)
        self.assert_rejected(audit_answer(FinalAnswer("done", [1]), gd.ledger), IssueCode.INVALID_ANSWER)
        self.assert_rejected(audit_answer(FinalAnswer("  ", (Claim(ClaimKind.FACT, "f", ("ev_1",)),)),
                                          gd.ledger), IssueCode.INVALID_ANSWER)
        self.assert_rejected(self.audit(gd, "claim as a string"), IssueCode.INVALID_ANSWER)
        self.assert_rejected(self.audit(gd, Claim("FACT", "f", ("ev_1",))), IssueCode.INVALID_ANSWER)
        for junk in ("The model is valid!", None, {"claims": []}, 42):
            self.assert_rejected(audit_answer(junk, gd.ledger), IssueCode.INVALID_ANSWER)

    def test_empty_ledger_cannot_ground_anything(self):
        ledger = Ledger()
        r = audit_answer(FinalAnswer("done", (Claim(ClaimKind.FACT, "f", ("ev_1",)),)), ledger)
        self.assert_rejected(r, IssueCode.UNKNOWN_EVIDENCE_ID)


class AuditResultInvariantTests(unittest.TestCase):
    def test_verified_and_no_evidence_cannot_carry_issues(self):
        from sysml_agent import Issue
        issue = Issue(IssueCode.INVALID_ANSWER, "x")
        for outcome in (Outcome.VERIFIED, Outcome.NO_EVIDENCE):
            with self.assertRaises(ValueError):
                AuditResult(outcome, (issue,))

    def test_rejected_requires_an_issue(self):
        with self.assertRaises(ValueError):
            AuditResult(Outcome.REJECTED)

    def test_outcome_must_be_an_outcome(self):
        with self.assertRaises(ValueError):
            AuditResult("VERIFIED")

    def test_audit_requires_a_real_ledger(self):
        with self.assertRaises(TypeError):
            audit_answer(NoEvidenceAnswer("x"), [])


if __name__ == "__main__":
    unittest.main()
