"""Milestone 1 tests: determinism, valid operations, and rejections.

Runs with either:  python -m unittest -v     or     pytest -v
"""
import unittest
from dataclasses import FrozenInstanceError

from sysml_agent import (
    AddRequirement, AddSatisfy, IssueCode, Model, RenameElement,
    build_mock_model, inspect_model, propose_operation, validate_candidate,
)


def codes(result) -> set:
    return {i.code for i in result.issues}


def propose_and_validate(operation, model=None):
    model = model or build_mock_model()
    proposal = propose_operation(model, operation)
    assert proposal.ok, f"proposal unexpectedly rejected: {proposal.issues}"
    return proposal, validate_candidate(proposal.candidate)


class BaselineModelTests(unittest.TestCase):
    def test_mock_model_is_valid(self):
        result = validate_candidate(build_mock_model())
        self.assertTrue(result.passed)
        self.assertEqual(result.issues, ())

    def test_mock_model_shape(self):
        m = build_mock_model()
        self.assertEqual(len(m.parts), 6)
        self.assertEqual(len(m.requirements), 5)
        self.assertEqual(len(m.satisfies), 4)

    def test_model_is_immutable(self):
        m = build_mock_model()
        with self.assertRaises(FrozenInstanceError):
            m.name = "hacked"
        with self.assertRaises(FrozenInstanceError):
            m.parts[0].domain = "power"


class DeterminismTests(unittest.TestCase):
    def test_builder_and_fingerprint_are_stable(self):
        self.assertEqual(build_mock_model(), build_mock_model())
        self.assertEqual(build_mock_model().fingerprint(), build_mock_model().fingerprint())

    def test_inspect_is_deterministic(self):
        m = build_mock_model()
        self.assertEqual(inspect_model(m), inspect_model(m))
        self.assertEqual(inspect_model(m, "R-001"), inspect_model(m, "R-001"))

    def test_propose_is_deterministic(self):
        op = AddSatisfy("R-005", "P-NAV")
        self.assertEqual(propose_operation(build_mock_model(), op),
                         propose_operation(build_mock_model(), op))

    def test_validate_is_deterministic_even_with_many_issues(self):
        m = build_mock_model()
        for op in (AddRequirement("R-001", "Dup", "x", "telepathy"),
                   AddSatisfy("R-999", "P-999"),
                   AddSatisfy("P-BAT", "R-002"),
                   AddSatisfy("R-005", "P-BAT")):
            m = propose_operation(m, op).candidate
        first, second = validate_candidate(m), validate_candidate(m)
        self.assertEqual(first, second)
        self.assertFalse(first.passed)
        self.assertEqual(first.issues, tuple(sorted(
            first.issues, key=lambda i: (i.element_id or "", i.code, i.message))))


class InspectTests(unittest.TestCase):
    def test_full_inspect_returns_exact_facts(self):
        r = inspect_model(build_mock_model())
        self.assertTrue(r.ok)
        self.assertEqual([x.id for x in r.requirements],
                         ["R-001", "R-002", "R-003", "R-004", "R-005"])
        self.assertEqual(r.unsatisfied_requirement_ids, ("R-005",))
        self.assertEqual(len(r.satisfies), 4)

    def test_inspect_single_requirement(self):
        r = inspect_model(build_mock_model(), "R-001")
        self.assertTrue(r.ok)
        self.assertEqual(r.requirements[0].text,
                         "The rover shall operate for at least 4 hours on a single battery charge.")
        self.assertEqual([(s.requirement_id, s.part_id) for s in r.satisfies],
                         [("R-001", "P-BAT")])
        self.assertEqual(r.unsatisfied_requirement_ids, ())

    def test_inspect_part_lists_incoming_links(self):
        r = inspect_model(build_mock_model(), "P-MOT")
        self.assertTrue(r.ok)
        self.assertEqual(r.parts[0].domain, "propulsion")
        self.assertEqual([s.requirement_id for s in r.satisfies], ["R-002"])

    def test_inspect_unknown_id_is_rejected(self):
        r = inspect_model(build_mock_model(), "R-404")
        self.assertFalse(r.ok)
        self.assertEqual(codes(r), {IssueCode.TARGET_NOT_FOUND})
        self.assertEqual(r.requirements, ())

    def test_inspect_non_model_is_rejected(self):
        r = inspect_model(None)
        self.assertFalse(r.ok)
        self.assertEqual(codes(r), {IssueCode.INVALID_INPUT})


class ValidOperationTests(unittest.TestCase):
    def test_add_requirement_valid(self):
        p, v = propose_and_validate(AddRequirement(
            "R-006", "Payload", "The rover shall carry a 2 kg payload.", "propulsion"))
        self.assertEqual(len(p.candidate.requirements), 6)
        self.assertTrue(v.passed)

    def test_add_satisfy_valid_closes_the_gap(self):
        p, v = propose_and_validate(AddSatisfy("R-005", "P-NAV"))
        self.assertTrue(v.passed)
        self.assertEqual(inspect_model(p.candidate).unsatisfied_requirement_ids, ())

    def test_rename_valid(self):
        p, v = propose_and_validate(RenameElement("P-BAT", "MainBattery"))
        self.assertTrue(v.passed)
        self.assertEqual(inspect_model(p.candidate, "P-BAT").parts[0].name, "MainBattery")

    def test_validation_is_bound_to_candidate_fingerprint(self):
        p, v = propose_and_validate(AddSatisfy("R-005", "P-NAV"))
        self.assertEqual(v.candidate_fingerprint, p.candidate_fingerprint)
        self.assertNotEqual(v.candidate_fingerprint, build_mock_model().fingerprint())

    def test_propose_never_mutates_original(self):
        original = build_mock_model()
        before = original.fingerprint()
        for op in (AddRequirement("R-006", "X", "x", "power"),
                   AddSatisfy("R-005", "P-NAV"),
                   RenameElement("R-001", "Renamed")):
            p = propose_operation(original, op)
            self.assertIsNot(p.candidate, original)
        self.assertEqual(original.fingerprint(), before)
        self.assertEqual(original, build_mock_model())


class ProposalRejectionTests(unittest.TestCase):
    def test_rename_unknown_id_rejected(self):
        p = propose_operation(build_mock_model(), RenameElement("P-404", "Ghost"))
        self.assertFalse(p.ok)
        self.assertIsNone(p.candidate)
        self.assertEqual(codes(p), {IssueCode.TARGET_NOT_FOUND})

    def test_rename_blank_name_rejected(self):
        p = propose_operation(build_mock_model(), RenameElement("P-BAT", "   "))
        self.assertFalse(p.ok)
        self.assertEqual(codes(p), {IssueCode.EMPTY_NAME})

    def test_unsupported_operation_rejected(self):
        for bad in ("delete everything", {"op": "AddSatisfy"}, None, 42):
            p = propose_operation(build_mock_model(), bad)
            self.assertFalse(p.ok)
            self.assertIsNone(p.candidate)
            self.assertEqual(codes(p), {IssueCode.UNSUPPORTED_OPERATION})

    def test_non_model_rejected(self):
        p = propose_operation("not a model", AddSatisfy("R-005", "P-NAV"))
        self.assertFalse(p.ok)
        self.assertEqual(codes(p), {IssueCode.INVALID_INPUT})


class ValidationRejectionTests(unittest.TestCase):
    def assert_rejected(self, operation, expected_codes):
        _, v = propose_and_validate(operation)
        self.assertFalse(v.passed)
        self.assertEqual(codes(v), set(expected_codes))
        for issue in v.issues:
            self.assertTrue(issue.message.strip())
        return v

    def test_duplicate_requirement_id(self):
        v = self.assert_rejected(AddRequirement("R-001", "Dup", "x", "power"),
                                 {IssueCode.DUPLICATE_ID})
        self.assertEqual(v.issues[0].element_id, "R-001")

    def test_duplicate_id_across_element_kinds(self):
        self.assert_rejected(AddRequirement("P-BAT", "Clash", "x", "power"),
                             {IssueCode.DUPLICATE_ID})

    def test_missing_requirement_id(self):
        self.assert_rejected(AddSatisfy("R-999", "P-BAT"), {IssueCode.MISSING_REQUIREMENT})

    def test_missing_part_id(self):
        self.assert_rejected(AddSatisfy("R-005", "P-999"), {IssueCode.MISSING_PART})

    def test_wrong_type_part_used_as_requirement(self):
        self.assert_rejected(AddSatisfy("P-BAT", "P-MOT"), {IssueCode.WRONG_ELEMENT_TYPE})

    def test_wrong_type_requirement_used_as_part(self):
        self.assert_rejected(AddSatisfy("R-005", "R-001"), {IssueCode.WRONG_ELEMENT_TYPE})

    def test_domain_mismatch(self):
        v = self.assert_rejected(AddSatisfy("R-005", "P-BAT"), {IssueCode.DOMAIN_MISMATCH})
        self.assertIn("navigation", v.issues[0].message)
        self.assertIn("power", v.issues[0].message)

    def test_unknown_domain(self):
        self.assert_rejected(AddRequirement("R-006", "Odd", "x", "telepathy"),
                             {IssueCode.UNKNOWN_DOMAIN})

    def test_duplicate_satisfy_link(self):
        self.assert_rejected(AddSatisfy("R-001", "P-BAT"), {IssueCode.DUPLICATE_SATISFY})

    def test_validate_non_model_fails(self):
        for bad in (None, "model", {"parts": []}):
            v = validate_candidate(bad)
            self.assertFalse(v.passed)
            self.assertIsNone(v.candidate_fingerprint)
            self.assertEqual(codes(v), {IssueCode.INVALID_INPUT})

    def test_empty_model_is_trivially_valid_but_says_what_was_checked(self):
        v = validate_candidate(Model(name="Empty"))
        self.assertTrue(v.passed)
        self.assertGreater(len(v.rules_checked), 0)


if __name__ == "__main__":
    unittest.main()
