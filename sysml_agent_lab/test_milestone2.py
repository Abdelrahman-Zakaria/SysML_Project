"""Milestone 2 tests: registry whitelist, schema validation, dispatcher envelope.

Runs with either:  python -m unittest -v     or     pytest -v
"""
import copy
import unittest
from dataclasses import replace

from sysml_agent import (
    DEFAULT_REGISTRY, ALLOWED_TOOL_NAMES, ArgSchema, DispatchEnvelope, InspectResult,
    Issue, IssueCode, Model, ProposalResult, Status, ToolContext, ToolRegistry,
    ValidationResult, build_mock_model, dispatch, parse_operation, validate_args,
    FieldSpec,
)


def ctx(candidate=None) -> ToolContext:
    return ToolContext(model=build_mock_model(), candidate=candidate)


def codes(env) -> set:
    return {i.code for i in env.issues}


def registry_with(name: str, **overrides) -> ToolRegistry:
    return ToolRegistry(tuple(replace(t, **overrides) if t.name == name else t
                              for t in DEFAULT_REGISTRY.tools))


def propose(op: dict):
    return dispatch("propose_operation", {"operation": op}, ctx())


class RegistryTests(unittest.TestCase):
    def test_exactly_the_three_whitelisted_tools(self):
        self.assertEqual(DEFAULT_REGISTRY.names(),
                         ("inspect_model", "propose_operation", "validate_candidate"))
        self.assertEqual(set(DEFAULT_REGISTRY.names()), ALLOWED_TOOL_NAMES)

    def test_unknown_name_is_not_in_registry(self):
        self.assertIsNone(DEFAULT_REGISTRY.get("delete_model"))
        self.assertIsNone(DEFAULT_REGISTRY.get(None))

    def test_registry_refuses_fabricated_tool_specs(self):
        spec = DEFAULT_REGISTRY.get("inspect_model")
        with self.assertRaises(ValueError):
            ToolRegistry((replace(spec, name="delete_model"),))

    def test_registry_refuses_duplicates(self):
        spec = DEFAULT_REGISTRY.get("inspect_model")
        with self.assertRaises(ValueError):
            ToolRegistry((spec, spec))


class ValidCallTests(unittest.TestCase):
    def test_inspect_whole_model_ok(self):
        env = dispatch("inspect_model", {}, ctx())
        self.assertEqual(env.status, Status.OK)
        self.assertIsInstance(env.result, InspectResult)
        self.assertEqual(env.result.unsatisfied_requirement_ids, ("R-005",))

    def test_inspect_one_element_ok(self):
        env = dispatch("inspect_model", {"element_id": "R-001"}, ctx())
        self.assertTrue(env.ok)
        self.assertEqual(env.result.requirements[0].id, "R-001")

    def test_propose_converts_raw_dict_to_typed_operation(self):
        env = propose({"type": "AddSatisfy", "requirement_id": "R-005", "part_id": "P-NAV"})
        self.assertEqual(env.status, Status.OK)
        self.assertIsInstance(env.result, ProposalResult)
        self.assertIsInstance(env.result.candidate, Model)
        self.assertEqual(type(env.result.operation).__name__, "AddSatisfy")

    def test_all_three_operation_types_dispatch(self):
        for op in ({"type": "AddRequirement", "id": "R-006", "name": "Payload",
                    "text": "The rover shall carry 2 kg.", "domain": "propulsion"},
                   {"type": "AddSatisfy", "requirement_id": "R-005", "part_id": "P-NAV"},
                   {"type": "RenameElement", "element_id": "P-BAT", "new_name": "MainBattery"}):
            self.assertTrue(propose(op).ok, op)

    def test_full_chain_propose_then_validate_with_context(self):
        prop = propose({"type": "AddSatisfy", "requirement_id": "R-005", "part_id": "P-NAV"})
        # The harness, not the LLM, carries the candidate forward.
        env = dispatch("validate_candidate", {}, ctx(candidate=prop.result.candidate))
        self.assertEqual(env.status, Status.OK)
        self.assertIsInstance(env.result, ValidationResult)
        self.assertTrue(env.result.passed)
        self.assertEqual(env.result.candidate_fingerprint, prop.result.candidate_fingerprint)

    def test_dispatch_is_deterministic_and_does_not_mutate_args(self):
        raw = {"operation": {"type": "RenameElement", "element_id": "P-BAT", "new_name": "X"}}
        snapshot = copy.deepcopy(raw)
        a = dispatch("propose_operation", raw, ctx())
        b = dispatch("propose_operation", raw, ctx())
        self.assertEqual(a, b)
        self.assertEqual(raw, snapshot)

    def test_context_model_is_never_mutated(self):
        c = ctx()
        before = c.model.fingerprint()
        propose_env = dispatch("propose_operation", {"operation": {
            "type": "AddSatisfy", "requirement_id": "R-005", "part_id": "P-NAV"}}, c)
        self.assertTrue(propose_env.ok)
        self.assertEqual(c.model.fingerprint(), before)


class UnknownToolTests(unittest.TestCase):
    def test_fabricated_tool_names_are_rejected(self):
        for bad in ("delete_model", "INSPECT_MODEL", "inspect_model ", "", "validate",
                    None, 123, ["inspect_model"], {"name": "inspect_model"}):
            env = dispatch(bad, {}, ctx())
            self.assertEqual(env.status, Status.REJECTED, bad)
            self.assertEqual(codes(env), {IssueCode.UNKNOWN_TOOL}, bad)
            self.assertIsNone(env.result)


class ArgumentValidationTests(unittest.TestCase):
    def assert_rejected(self, env, expected_code):
        self.assertEqual(env.status, Status.REJECTED)
        self.assertIn(expected_code, codes(env))
        self.assertIsNone(env.result)
        self.assertTrue(all(i.message.strip() for i in env.issues))

    def test_arguments_must_be_a_json_object(self):
        for bad in (None, "element_id=R-001", [], 5, ("a",)):
            self.assert_rejected(dispatch("inspect_model", bad, ctx()),
                                 IssueCode.INVALID_ARGUMENTS)

    def test_extra_keys_rejected(self):
        self.assert_rejected(dispatch("inspect_model",
                                      {"element_id": "R-001", "force": True}, ctx()),
                             IssueCode.UNEXPECTED_ARGUMENT)

    def test_llm_cannot_smuggle_a_model_into_validate(self):
        env = dispatch("validate_candidate", {"candidate": {"parts": []}},
                       ctx(candidate=build_mock_model()))
        self.assert_rejected(env, IssueCode.UNEXPECTED_ARGUMENT)

    def test_missing_required_field(self):
        self.assert_rejected(dispatch("propose_operation", {}, ctx()),
                             IssueCode.MISSING_ARGUMENT)

    def test_wrong_types(self):
        for tool, args in (("inspect_model", {"element_id": 5}),
                           ("inspect_model", {"element_id": None}),
                           ("inspect_model", {"element_id": True}),
                           ("inspect_model", {"element_id": ["R-001"]}),
                           ("propose_operation", {"operation": "AddSatisfy"}),
                           ("propose_operation", {"operation": ["AddSatisfy"]})):
            env = dispatch(tool, args, ctx())
            self.assertEqual(env.status, Status.REJECTED, args)
            self.assertTrue(codes(env) & {IssueCode.WRONG_TYPE, IssueCode.INVALID_ARGUMENTS}, args)

    def test_empty_strings_rejected(self):
        self.assert_rejected(dispatch("inspect_model", {"element_id": "   "}, ctx()),
                             IssueCode.EMPTY_VALUE)

    def test_unknown_operation_type(self):
        for bad in ("DeleteEverything", "addsatisfy", ""):
            self.assert_rejected(propose({"type": bad}), IssueCode.UNSUPPORTED_OPERATION)

    def test_operation_type_missing_or_wrong_type(self):
        self.assert_rejected(propose({"requirement_id": "R-005", "part_id": "P-NAV"}),
                             IssueCode.MISSING_ARGUMENT)
        self.assert_rejected(propose({"type": 3}), IssueCode.WRONG_TYPE)

    def test_operation_field_errors_are_all_reported_at_once(self):
        env = propose({"type": "AddRequirement", "id": "R-006", "name": "N",
                       "domain": "power", "priority": "high"})  # no text, extra key
        self.assertEqual(env.status, Status.REJECTED)
        self.assertEqual(codes(env), {IssueCode.MISSING_ARGUMENT, IssueCode.UNEXPECTED_ARGUMENT})

    def test_operation_field_wrong_type(self):
        self.assert_rejected(propose({"type": "AddSatisfy", "requirement_id": 7,
                                      "part_id": "P-NAV"}), IssueCode.WRONG_TYPE)

    def test_blank_rename_is_stopped_at_the_schema(self):
        self.assert_rejected(propose({"type": "RenameElement", "element_id": "P-BAT",
                                      "new_name": "  "}), IssueCode.EMPTY_VALUE)

    def test_issues_are_sorted_deterministically(self):
        a = propose({"type": "AddRequirement", "zzz": 1, "aaa": 2})
        b = propose({"type": "AddRequirement", "aaa": 2, "zzz": 1})
        self.assertEqual(a.issues, b.issues)

    def test_schema_helpers_directly(self):
        schema = ArgSchema((FieldSpec("n", str), FieldSpec("k", dict, required=False)))
        self.assertEqual(validate_args(schema, {"n": "x"}), ({"n": "x"}, ()))
        clean, issues = validate_args(schema, {"n": "x", "bad": 1})
        self.assertEqual(clean, {})
        self.assertEqual(issues[0].code, IssueCode.UNEXPECTED_ARGUMENT)
        op, issues = parse_operation({"type": "AddSatisfy", "requirement_id": "R-1",
                                      "part_id": "P-1"})
        self.assertEqual(issues, ())
        self.assertEqual((op.requirement_id, op.part_id), ("R-1", "P-1"))


class PrerequisiteAndVerdictTests(unittest.TestCase):
    def test_validate_without_candidate_is_rejected(self):
        env = dispatch("validate_candidate", {}, ctx())
        self.assertEqual(env.status, Status.REJECTED)
        self.assertEqual(codes(env), {IssueCode.NO_CANDIDATE})

    def test_missing_model_is_rejected_by_the_tool(self):
        env = dispatch("inspect_model", {}, ToolContext(model=None))
        self.assertEqual(env.status, Status.REJECTED)
        self.assertEqual(codes(env), {IssueCode.INVALID_INPUT})

    def test_negative_tool_verdicts_are_never_ok(self):
        # inspect: unknown element
        env = dispatch("inspect_model", {"element_id": "R-404"}, ctx())
        self.assertEqual(env.status, Status.REJECTED)
        self.assertEqual(codes(env), {IssueCode.TARGET_NOT_FOUND})
        self.assertIsInstance(env.result, InspectResult)      # detail stays visible
        self.assertFalse(env.result.ok)
        # propose: rename of an unknown element
        env = propose({"type": "RenameElement", "element_id": "P-404", "new_name": "Ghost"})
        self.assertEqual(env.status, Status.REJECTED)
        self.assertEqual(codes(env), {IssueCode.TARGET_NOT_FOUND})

    def test_schema_valid_but_semantically_invalid_candidate_is_caught_by_validator(self):
        prop = propose({"type": "AddSatisfy", "requirement_id": "R-005", "part_id": "P-BAT"})
        self.assertTrue(prop.ok)   # well-formed, so the proposal tool accepts it...
        env = dispatch("validate_candidate", {}, ctx(candidate=prop.result.candidate))
        self.assertEqual(env.status, Status.REJECTED)   # ...but the validator does not
        self.assertEqual(codes(env), {IssueCode.DOMAIN_MISMATCH})
        self.assertFalse(env.result.passed)

    def test_unknown_domain_passes_schema_but_fails_validation(self):
        prop = propose({"type": "AddRequirement", "id": "R-006", "name": "Odd",
                        "text": "x", "domain": "telepathy"})
        self.assertTrue(prop.ok)
        env = dispatch("validate_candidate", {}, ctx(candidate=prop.result.candidate))
        self.assertEqual(env.status, Status.REJECTED)
        self.assertEqual(codes(env), {IssueCode.UNKNOWN_DOMAIN})

    def test_bad_harness_context_is_a_tool_error(self):
        env = dispatch("inspect_model", {}, "not a context")
        self.assertEqual(env.status, Status.TOOL_ERROR)


class InjectedToolFailureTests(unittest.TestCase):
    def test_crashing_tool_becomes_tool_error(self):
        def crash(*_a):
            raise RuntimeError("boom")
        env = dispatch("inspect_model", {}, ctx(), registry_with("inspect_model", func=crash))
        self.assertEqual(env.status, Status.TOOL_ERROR)
        self.assertEqual(codes(env), {IssueCode.TOOL_EXCEPTION})
        self.assertIn("boom", env.issues[0].message)
        self.assertIsNone(env.result)

    def test_crash_in_every_tool_is_contained(self):
        def crash(*_a):
            raise ZeroDivisionError("x")
        cand = build_mock_model()
        calls = {"inspect_model": {}, "propose_operation": {"operation": {
            "type": "AddSatisfy", "requirement_id": "R-005", "part_id": "P-NAV"}},
            "validate_candidate": {}}
        for name, args in calls.items():
            env = dispatch(name, args, ctx(candidate=cand), registry_with(name, func=crash))
            self.assertEqual(env.status, Status.TOOL_ERROR, name)

    def test_wrong_return_type_is_tool_error(self):
        for junk in (None, "OK", {"ok": True}, 42, True):
            env = dispatch("inspect_model", {}, ctx(),
                           registry_with("inspect_model", func=lambda *_a, j=junk: j))
            self.assertEqual(env.status, Status.TOOL_ERROR, junk)
            self.assertEqual(codes(env), {IssueCode.BAD_TOOL_RESULT})

    def test_malformed_issue_list_is_tool_error(self):
        bad = ValidationResult(False, None, (), ("just a string",))
        env = dispatch("validate_candidate", {}, ctx(candidate=build_mock_model()),
                       registry_with("validate_candidate", func=lambda *_a: bad))
        self.assertEqual(env.status, Status.TOOL_ERROR)

    def test_failure_without_explanation_is_still_rejected_with_an_issue(self):
        silent = ValidationResult(passed=False, candidate_fingerprint=None,
                                  rules_checked=(), issues=())
        env = dispatch("validate_candidate", {}, ctx(candidate=build_mock_model()),
                       registry_with("validate_candidate", func=lambda *_a: silent))
        self.assertEqual(env.status, Status.REJECTED)
        self.assertEqual(codes(env), {IssueCode.UNEXPLAINED_FAILURE})

    def test_keyboard_interrupt_is_not_swallowed(self):
        def interrupt(*_a):
            raise KeyboardInterrupt
        with self.assertRaises(KeyboardInterrupt):
            dispatch("inspect_model", {}, ctx(), registry_with("inspect_model", func=interrupt))


class EnvelopeInvariantTests(unittest.TestCase):
    def test_ok_requires_a_result(self):
        with self.assertRaises(ValueError):
            DispatchEnvelope(Status.OK, "inspect_model")

    def test_non_ok_requires_an_issue(self):
        for status in (Status.REJECTED, Status.TOOL_ERROR):
            with self.assertRaises(ValueError):
                DispatchEnvelope(status, "inspect_model")

    def test_status_must_be_a_status_member(self):
        with self.assertRaises(ValueError):
            DispatchEnvelope("OK", "inspect_model", result=object())

    def test_envelope_is_frozen(self):
        env = dispatch("inspect_model", {}, ctx())
        with self.assertRaises(Exception):
            env.status = Status.REJECTED


class NothingBadIsOkTests(unittest.TestCase):
    """Mini exit-gate for this layer: no bad call may produce Status.OK."""

    def test_battery_of_bad_calls(self):
        c = ctx()
        bad_calls = [
            ("delete_model", {}),
            (None, {}),
            ("inspect_model", None),
            ("inspect_model", {"nope": 1}),
            ("inspect_model", {"element_id": 9}),
            ("inspect_model", {"element_id": "R-404"}),
            ("propose_operation", {}),
            ("propose_operation", {"operation": {"type": "Nuke"}}),
            ("propose_operation", {"operation": {"type": "RenameElement",
                                                 "element_id": "P-404", "new_name": "G"}}),
            ("validate_candidate", {}),                       # no candidate yet
            ("validate_candidate", {"candidate": "x"}),
        ]
        for name, args in bad_calls:
            env = dispatch(name, args, c)
            self.assertFalse(env.ok, (name, args))
            self.assertNotEqual(env.status, Status.OK)
            self.assertTrue(env.issues, (name, args))


if __name__ == "__main__":
    unittest.main()
