"""Milestone 4 tests: scripted end-to-end agent runs.

Runs with either:  python -m unittest -v     or     pytest -v
"""
import json
import unittest
from dataclasses import replace

from sysml_agent import (
    DEFAULT_REGISTRY, AgentRunResult, AgentStatus, AuditResult, FailureReason, FinalAnswer,
    IssueCode, NoEvidenceAnswer, Outcome, ScriptedLLM, ScriptExhausted, ToolRegistry,
    build_mock_model, build_system_prompt, check_turn, run_agent,
)

MODEL = build_mock_model()
GOOD_OP = {"type": "AddSatisfy", "requirement_id": "R-005", "part_id": "P-NAV"}
BAD_OP = {"type": "AddSatisfy", "requirement_id": "R-005", "part_id": "P-BAT"}   # domain mismatch
TASK = "Make requirement R-005 satisfied and confirm the change is valid."


# ---- script helpers ------------------------------------------------------
def call(tool, **args):
    return {"type": "tool_call", "tool": tool, "args": args}


def last_obs(messages, tool, status="OK"):
    for m in reversed(messages):
        c = m["content"]
        if m["role"] == "tool" and c.get("tool") == tool and c.get("status") == status:
            return c
    raise AssertionError(f"no {status} observation from {tool}")


def final_valid(messages):
    """What a real model would do: read ids and the fingerprint out of observations."""
    prop = last_obs(messages, "propose_operation")
    val = last_obs(messages, "validate_candidate")
    return {"type": "final_answer", "summary": "R-005 is now satisfied by P-NAV.", "claims": [
        {"kind": "PROPOSAL", "text": "AddSatisfy R-005 -> P-NAV was proposed.",
         "evidence_ids": [prop["evidence_id"]],
         "candidate_fingerprint": prop["candidate_fingerprint"]},
        {"kind": "VALID", "text": "The proposed change is valid.",
         "evidence_ids": [prop["evidence_id"], val["evidence_id"]],
         "candidate_fingerprint": val["candidate_fingerprint"]}]}


def fact_answer(*ids):
    return {"type": "final_answer", "summary": "facts", "claims": [
        {"kind": "FACT", "text": "Model facts.", "evidence_ids": list(ids)}]}


def run(steps, repeat_last=False, **kw):
    llm = ScriptedLLM(steps, repeat_last=repeat_last)
    return run_agent(llm, TASK, MODEL, **kw), llm


def codes(result) -> set:
    return {i.code for i in result.issues}


def registry_with(name, **overrides):
    return ToolRegistry(tuple(replace(t, **overrides) if t.name == name else t
                              for t in DEFAULT_REGISTRY.tools))


# ---- the scripted fake itself ---------------------------------------------
class ScriptedLLMTests(unittest.TestCase):
    def test_replays_in_order_and_records_history(self):
        llm = ScriptedLLM([{"type": "a"}, {"type": "b"}])
        self.assertEqual(llm.next_step([1]), {"type": "a"})
        self.assertEqual(llm.next_step([1, 2]), {"type": "b"})
        self.assertEqual(llm.received, [[1], [1, 2]])

    def test_exhaustion_raises_unless_repeat_last(self):
        llm = ScriptedLLM([{"type": "a"}])
        llm.next_step([])
        with self.assertRaises(ScriptExhausted):
            llm.next_step([])
        looping = ScriptedLLM([{"type": "a"}], repeat_last=True)
        self.assertEqual([looping.next_step([]) for _ in range(3)], [{"type": "a"}] * 3)

    def test_empty_script_raises_even_with_repeat_last(self):
        with self.assertRaises(ScriptExhausted):
            ScriptedLLM([], repeat_last=True).next_step([])

    def test_callable_and_exception_steps(self):
        llm = ScriptedLLM([lambda msgs: {"n": len(msgs)}, RuntimeError("api down")])
        self.assertEqual(llm.next_step([1, 2, 3]), {"n": 3})
        with self.assertRaises(RuntimeError):
            llm.next_step([])

    def test_returned_steps_are_copies(self):
        llm = ScriptedLLM([{"type": "a", "args": {"k": 1}}], repeat_last=True)
        llm.next_step([])["args"]["k"] = 999
        self.assertEqual(llm.next_step([])["args"]["k"], 1)


class TurnEnvelopeTests(unittest.TestCase):
    def test_valid_turns(self):
        for turn in (call("inspect_model"), {"type": "tool_call", "tool": "x"},
                     fact_answer("ev_1"), {"type": "no_evidence", "reason": "r"}):
            self.assertEqual(check_turn(turn), (), turn)

    def test_malformed_turns(self):
        bad = ["text", None, 42, [], {}, {"type": 3}, {"type": "launch"},
               {"type": "tool_call"}, {"type": "tool_call", "tool": "t", "force": True},
               {"type": "final_answer", "claims": []}, {"type": "no_evidence"}]
        for turn in bad:
            issues = check_turn(turn)
            self.assertTrue(issues, turn)
            self.assertEqual({i.code for i in issues}, {IssueCode.MALFORMED_TURN})


class PromptTests(unittest.TestCase):
    def test_system_prompt_lists_tools_and_operations_deterministically(self):
        prompt = build_system_prompt()
        for needle in ("inspect_model", "propose_operation", "validate_candidate",
                       "AddRequirement", "AddSatisfy", "RenameElement", "no_evidence"):
            self.assertIn(needle, prompt)
        self.assertEqual(prompt, build_system_prompt())


# ---- 1. happy path --------------------------------------------------------
class HappyPathTests(unittest.TestCase):
    def setUp(self):
        self.result, self.llm = run([
            call("inspect_model"),
            call("propose_operation", operation=GOOD_OP),
            call("validate_candidate"),
            final_valid,
        ])

    def test_verified(self):
        r = self.result
        self.assertEqual(r.status, AgentStatus.VERIFIED)
        self.assertTrue(r.verified)
        self.assertIsInstance(r.answer, FinalAnswer)
        self.assertEqual(r.audit.outcome, Outcome.VERIFIED)
        self.assertIsNone(r.failure_reason)
        self.assertEqual(r.issues, ())
        self.assertEqual((r.calls_used, r.turns), (3, 4))

    def test_ledger_and_evidence_trail(self):
        r = self.result
        self.assertEqual([e.evidence_id for e in r.evidence], ["ev_1", "ev_2", "ev_3"])
        self.assertEqual([e.tool_name for e in r.evidence],
                         ["inspect_model", "propose_operation", "validate_candidate"])
        self.assertEqual(r.audit.cited_evidence_ids, ("ev_2", "ev_3"))

    def test_observations_are_structured_json(self):
        obs = last_obs(self.result.messages, "validate_candidate")
        self.assertEqual(set(obs), {"evidence_id", "tool", "status", "result", "issues",
                                    "candidate_fingerprint", "calls_remaining"})
        self.assertEqual(obs["status"], "OK")
        self.assertTrue(obs["result"]["passed"])
        self.assertEqual(obs["calls_remaining"], 5)

    def test_llm_only_ever_sees_plain_json(self):
        json.dumps(self.result.messages)                       # transcript
        for history in self.llm.received:
            json.dumps(history)                                # nothing like a Model leaks out
        self.assertEqual(self.llm.received[0][0]["role"], "system")
        self.assertEqual(self.llm.received[0][1], {"role": "user", "content": TASK})
        self.assertEqual([len(h) for h in self.llm.received], [2, 4, 6, 8])

    def test_harness_not_the_llm_carried_the_candidate_forward(self):
        # validate_candidate took no arguments and still validated the proposed candidate
        val = self.result.evidence[2]
        self.assertEqual(val.arguments, {})
        self.assertEqual(val.subject_fingerprint, self.result.evidence[1].candidate_fingerprint)

    def test_original_model_untouched_and_run_is_deterministic(self):
        self.assertEqual(MODEL, build_mock_model())
        again, _ = run([call("inspect_model"), call("propose_operation", operation=GOOD_OP),
                        call("validate_candidate"), final_valid])
        self.assertEqual(self.result, again)


# ---- 2. rejection recovery ------------------------------------------------
class RecoveryTests(unittest.TestCase):
    def test_domain_mismatch_then_self_correction(self):
        def fix(messages):
            seen = messages[-1]["content"]
            assert seen["status"] == "REJECTED" and seen["tool"] == "validate_candidate"
            assert seen["issues"][0]["code"] == "DOMAIN_MISMATCH"
            return call("propose_operation", operation=GOOD_OP)

        r, _ = run([call("propose_operation", operation=BAD_OP),    # ev_1 OK (well-formed)
                    call("validate_candidate"),                      # ev_2 REJECTED
                    fix,                                             # ev_3 OK
                    call("validate_candidate"),                      # ev_4 OK
                    final_valid])
        self.assertEqual(r.status, AgentStatus.VERIFIED)
        self.assertEqual([e.status.value for e in r.evidence], ["OK", "REJECTED", "OK", "OK"])
        self.assertEqual(r.audit.cited_evidence_ids, ("ev_3", "ev_4"))   # the failure is not cited

    def test_unknown_element_then_self_correction(self):
        def retry(messages):
            seen = messages[-1]["content"]
            assert seen["status"] == "REJECTED"
            assert seen["issues"][0]["code"] == "TARGET_NOT_FOUND"
            return call("inspect_model", element_id="R-001")

        r, _ = run([call("inspect_model", element_id="R-404"), retry, fact_answer("ev_2")])
        self.assertEqual(r.status, AgentStatus.VERIFIED)
        self.assertEqual([e.status.value for e in r.evidence], ["REJECTED", "OK"])

    def test_rejected_proposal_leaves_the_candidate_unchanged(self):
        r, _ = run([call("propose_operation", operation=GOOD_OP),
                    call("propose_operation", operation={"type": "RenameElement",
                                                         "element_id": "P-404", "new_name": "Ghost"}),
                    call("validate_candidate"), final_valid])
        self.assertEqual(r.status, AgentStatus.VERIFIED)
        self.assertEqual(r.evidence[2].subject_fingerprint, r.evidence[0].candidate_fingerprint)

    def test_proposals_are_not_stacked(self):
        r, _ = run([call("propose_operation", operation=GOOD_OP),
                    call("propose_operation", operation={"type": "RenameElement",
                                                         "element_id": "P-BAT", "new_name": "Main"}),
                    call("validate_candidate"),
                    lambda m: {"type": "no_evidence", "reason": "stop"}])
        self.assertEqual(r.evidence[2].subject_fingerprint, r.evidence[1].candidate_fingerprint)
        self.assertNotEqual(r.evidence[2].subject_fingerprint, r.evidence[0].candidate_fingerprint)

    def test_malformed_turn_is_fed_back_and_the_run_recovers(self):
        r, llm = run(["I think the answer is 42", call("inspect_model"), fact_answer("ev_1")])
        self.assertEqual(r.status, AgentStatus.VERIFIED)
        self.assertEqual((r.calls_used, len(r.evidence), r.turns), (1, 1, 3))
        feedback = llm.received[1][-1]["content"]
        self.assertEqual(feedback["status"], "MALFORMED_TURN")

    def test_tool_argument_errors_are_observations_not_malformed_turns(self):
        r, _ = run([{"type": "tool_call", "tool": "inspect_model", "args": "R-001"},
                    {"type": "no_evidence", "reason": "could not call the tool", "evidence_ids": ["ev_1"]}])
        self.assertEqual(r.status, AgentStatus.NO_EVIDENCE)
        self.assertEqual(r.evidence[0].status.value, "REJECTED")
        self.assertEqual(r.evidence[0].issues[0].code, IssueCode.INVALID_ARGUMENTS)

    def test_rejected_final_answer_can_be_retried_when_allowed(self):
        steps = [call("inspect_model"), fact_answer("ev_99"), fact_answer("ev_1")]
        r, llm = run(steps, max_answer_attempts=2)
        self.assertEqual(r.status, AgentStatus.VERIFIED)
        feedback = llm.received[2][-1]["content"]
        self.assertEqual(feedback["status"], "ANSWER_REJECTED")
        self.assertEqual(feedback["attempts_remaining"], 1)
        self.assertEqual(feedback["issues"][0]["code"], "UNKNOWN_EVIDENCE_ID")
        strict, _ = run(steps)                      # default: one attempt only
        self.assertEqual(strict.status, AgentStatus.FAILED)


# ---- 3. no-evidence path --------------------------------------------------
class NoEvidenceTests(unittest.TestCase):
    def test_model_lacks_the_requested_info(self):
        r, _ = run([call("inspect_model", element_id="R-404"),
                    {"type": "no_evidence", "reason": "R-404 does not exist in the model.",
                     "evidence_ids": ["ev_1"]}])
        self.assertEqual(r.status, AgentStatus.NO_EVIDENCE)
        self.assertIsInstance(r.answer, NoEvidenceAnswer)
        self.assertEqual(r.audit.outcome, Outcome.NO_EVIDENCE)
        self.assertEqual(r.audit.cited_evidence_ids, ("ev_1",))
        self.assertFalse(r.verified)

    def test_immediate_no_evidence_without_any_call(self):
        r, _ = run([{"type": "no_evidence", "reason": "Nothing was inspected."}])
        self.assertEqual((r.status, r.calls_used, r.evidence), (AgentStatus.NO_EVIDENCE, 0, ()))

    def test_fabricated_tool_name_cannot_become_a_result(self):
        r, _ = run([call("delete_model"), {"type": "no_evidence", "reason": "no such tool"}])
        self.assertEqual(r.status, AgentStatus.NO_EVIDENCE)
        self.assertEqual(r.evidence[0].issues[0].code, IssueCode.UNKNOWN_TOOL)


# ---- 4. failure paths -----------------------------------------------------
class FailureTests(unittest.TestCase):
    def test_infinite_loop_hits_the_budget(self):
        r, llm = run([call("inspect_model")], repeat_last=True, max_calls=3)
        self.assertEqual(r.status, AgentStatus.FAILED)
        self.assertEqual(r.failure_reason, FailureReason.BUDGET_EXHAUSTED)
        self.assertEqual(codes(r), {IssueCode.BUDGET_EXHAUSTED})
        self.assertEqual((r.calls_used, len(r.evidence), r.turns), (3, 4, 4))
        self.assertEqual(r.evidence[-1].issues[0].code, IssueCode.BUDGET_EXHAUSTED)
        self.assertIsNone(r.answer)
        self.assertEqual(r.messages[-1]["content"]["status"], "REJECTED")

    def test_answer_is_still_allowed_after_the_last_call(self):
        r, _ = run([call("inspect_model"), fact_answer("ev_1")], max_calls=1)
        self.assertEqual(r.status, AgentStatus.VERIFIED)

    def test_unvalidated_validity_claim_fails(self):
        r, _ = run([call("propose_operation", operation=GOOD_OP),
                    lambda m: {"type": "final_answer", "summary": "valid!", "claims": [
                        {"kind": "VALID", "text": "It is valid.", "evidence_ids": ["ev_1"],
                         "candidate_fingerprint": last_obs(m, "propose_operation")["candidate_fingerprint"]}]}])
        self.assertEqual(r.status, AgentStatus.FAILED)
        self.assertEqual(r.failure_reason, FailureReason.ANSWER_REJECTED)
        self.assertIn(IssueCode.NOT_VALIDATED, codes(r))
        self.assertEqual(r.audit.outcome, Outcome.REJECTED)
        self.assertIsNone(r.answer)

    def test_validity_claim_after_failed_validation_fails(self):
        r, _ = run([call("propose_operation", operation=BAD_OP), call("validate_candidate"),
                    lambda m: {"type": "final_answer", "summary": "valid!", "claims": [
                        {"kind": "VALID", "text": "It is valid.", "evidence_ids": ["ev_1", "ev_2"],
                         "candidate_fingerprint": last_obs(m, "propose_operation")["candidate_fingerprint"]}]}])
        self.assertEqual(r.status, AgentStatus.FAILED)
        self.assertIn(IssueCode.CITES_FAILED_EVIDENCE, codes(r))

    def test_fabricated_evidence_fails(self):
        r, _ = run([fact_answer("ev_99")])
        self.assertEqual(r.status, AgentStatus.FAILED)
        self.assertEqual(codes(r), {IssueCode.UNKNOWN_EVIDENCE_ID})

    def test_claim_without_evidence_fails(self):
        r, _ = run([call("inspect_model"), fact_answer()])
        self.assertEqual(r.status, AgentStatus.FAILED)
        self.assertIn(IssueCode.UNSUPPORTED_CLAIM, codes(r))

    def test_answer_citing_a_crashed_tool_fails(self):
        def crash(*_a):
            raise RuntimeError("boom")
        reg = registry_with("inspect_model", func=crash)
        llm = ScriptedLLM([call("inspect_model"), fact_answer("ev_1")])
        r = run_agent(llm, TASK, MODEL, registry=reg)
        self.assertEqual(r.evidence[0].status.value, "TOOL_ERROR")
        self.assertEqual(r.status, AgentStatus.FAILED)
        self.assertIn(IssueCode.CITES_FAILED_EVIDENCE, codes(r))

    def test_junk_claims_fail_rather_than_crash(self):
        junk_answers = [
            {"type": "final_answer", "summary": "x", "claims": []},
            {"type": "final_answer", "summary": "x", "claims": "ev_1"},
            {"type": "final_answer", "summary": "x", "claims": ["trust me"]},
            {"type": "final_answer", "summary": "x",
             "claims": [{"kind": "TRUTH", "text": "t", "evidence_ids": ["ev_1"]}]},
            {"type": "final_answer", "summary": "x",
             "claims": [{"kind": "FACT", "text": "t", "evidence_ids": [1]}]},
            {"type": "final_answer", "summary": "x",
             "claims": [{"kind": "FACT", "text": "t", "evidence_ids": "ev_1"}]},
            {"type": "final_answer", "summary": "x",
             "claims": [{"kind": "FACT", "text": "t", "extra": 1}]},
            {"type": "final_answer", "summary": "", "claims": [
                {"kind": "FACT", "text": "t", "evidence_ids": ["ev_1"]}]},
            {"type": "no_evidence", "reason": ""},
            {"type": "no_evidence", "reason": "r", "evidence_ids": ["ev_42"]},
        ]
        for answer in junk_answers:
            r, _ = run([call("inspect_model"), answer])
            self.assertEqual(r.status, AgentStatus.FAILED, answer)
            self.assertEqual(r.failure_reason, FailureReason.ANSWER_REJECTED, answer)

    def test_never_verified_when_the_audit_rejects(self):
        for steps in ([fact_answer("ev_99")],
                      [call("propose_operation", operation=BAD_OP), fact_answer("ev_1")],
                      [call("inspect_model", element_id="R-404"), fact_answer("ev_1")]):
            r, _ = run(steps)
            self.assertNotEqual(r.status, AgentStatus.VERIFIED)
            self.assertEqual(r.status, AgentStatus.FAILED)

    def test_llm_failures_are_failed_runs(self):
        r, _ = run([RuntimeError("api down")])
        self.assertEqual((r.status, r.failure_reason), (AgentStatus.FAILED, FailureReason.LLM_ERROR))
        self.assertEqual(codes(r), {IssueCode.LLM_ERROR})
        r, _ = run([call("inspect_model")])                       # script ends without an answer
        self.assertEqual(r.failure_reason, FailureReason.LLM_ERROR)
        self.assertEqual(r.calls_used, 1)

    def test_keyboard_interrupt_from_the_llm_is_not_swallowed(self):
        def interrupt(_m):
            raise KeyboardInterrupt
        with self.assertRaises(KeyboardInterrupt):
            run([interrupt])

    def test_endless_malformed_turns_fail(self):
        r, _ = run([None], repeat_last=True, max_malformed_turns=3)
        self.assertEqual(r.failure_reason, FailureReason.TOO_MANY_MALFORMED_TURNS)
        self.assertEqual((r.turns, r.calls_used, r.evidence), (4, 0, ()))
        self.assertEqual(codes(r), {IssueCode.MALFORMED_TURN})

    def test_each_malformed_shape_fails_when_no_retries_are_allowed(self):
        for turn in ["text", None, 42, [], {}, {"type": "launch"}, {"type": "tool_call"},
                     {"type": "tool_call", "tool": "inspect_model", "force": True},
                     {"type": "final_answer", "claims": []}]:
            r, _ = run([turn], max_malformed_turns=0)
            self.assertEqual(r.status, AgentStatus.FAILED, turn)
            self.assertEqual(r.failure_reason, FailureReason.TOO_MANY_MALFORMED_TURNS, turn)


# ---- result invariants and configuration ---------------------------------
class ResultInvariantTests(unittest.TestCase):
    def test_verified_requires_a_verified_audit(self):
        fa = FinalAnswer("s", ())
        with self.assertRaises(ValueError):
            AgentRunResult(AgentStatus.VERIFIED, fa, None)
        with self.assertRaises(ValueError):
            AgentRunResult(AgentStatus.VERIFIED, fa, AuditResult(Outcome.NO_EVIDENCE))
        with self.assertRaises(ValueError):
            AgentRunResult(AgentStatus.VERIFIED, NoEvidenceAnswer("r"), AuditResult(Outcome.VERIFIED))
        AgentRunResult(AgentStatus.VERIFIED, fa, AuditResult(Outcome.VERIFIED))   # the legal shape

    def test_no_evidence_shape(self):
        with self.assertRaises(ValueError):
            AgentRunResult(AgentStatus.NO_EVIDENCE, FinalAnswer("s", ()), AuditResult(Outcome.NO_EVIDENCE))
        AgentRunResult(AgentStatus.NO_EVIDENCE, NoEvidenceAnswer("r"), AuditResult(Outcome.NO_EVIDENCE))

    def test_failed_needs_a_reason_and_issues_and_no_answer(self):
        from sysml_agent import Issue
        issue = Issue(IssueCode.LLM_ERROR, "x")
        with self.assertRaises(ValueError):
            AgentRunResult(AgentStatus.FAILED)
        with self.assertRaises(ValueError):
            AgentRunResult(AgentStatus.FAILED, failure_reason=FailureReason.LLM_ERROR)
        with self.assertRaises(ValueError):
            AgentRunResult(AgentStatus.FAILED, answer=FinalAnswer("s", ()),
                           failure_reason=FailureReason.LLM_ERROR, issues=(issue,))
        AgentRunResult(AgentStatus.FAILED, failure_reason=FailureReason.LLM_ERROR, issues=(issue,))

    def test_status_must_be_a_member(self):
        with self.assertRaises(ValueError):
            AgentRunResult("VERIFIED")


class ConfigAndIsolationTests(unittest.TestCase):
    def test_bad_configuration_is_refused(self):
        llm = ScriptedLLM([])
        for kwargs in ({"max_calls": -1}, {"max_calls": "3"}, {"max_malformed_turns": -1},
                       {"max_answer_attempts": 0}, {"max_answer_attempts": True}):
            with self.assertRaises(ValueError, msg=str(kwargs)):
                run_agent(llm, TASK, MODEL, **kwargs)
        with self.assertRaises(ValueError):
            run_agent(llm, "  ", MODEL)

    def test_the_llm_cannot_corrupt_the_harness_history(self):
        def vandal(messages):
            messages.clear()
            return call("inspect_model")
        r, _ = run([vandal, fact_answer("ev_1")])
        self.assertEqual(r.status, AgentStatus.VERIFIED)
        self.assertEqual(r.messages[0]["role"], "system")
        self.assertEqual(len(r.messages), 5)


if __name__ == "__main__":
    unittest.main()
