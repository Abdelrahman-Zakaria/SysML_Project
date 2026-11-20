"""Run the real NVIDIA Nemotron agent and save the exact raw JSON returned by NVIDIA."""
import json
from pathlib import Path

from sysml_agent import FinalAnswer, NoEvidenceAnswer, NvidiaLLM, build_mock_model, run_agent


def run_task(title: str, task: str, raw_output_file: str) -> None:
    llm = NvidiaLLM()
    result = run_agent(
        llm=llm,
        task=task,
        model=build_mock_model(),
        max_calls=8,
        max_malformed_turns=3,
        max_answer_attempts=2,
    )

    print(f"\n=== {title} ===")
    print(f"Status : {result.status.value} ({result.calls_used} tool calls, {result.turns} LLM turns)")
    if isinstance(result.answer, FinalAnswer):
        print(f"Summary: {result.answer.summary}")
    elif isinstance(result.answer, NoEvidenceAnswer):
        print(f"Reason : {result.answer.reason}")
    else:
        print(f"Failure: {result.failure_reason.value} -> {[i.message for i in result.issues]}")

    # Write the untouched raw JSON returned by NVIDIA's API on each turn
    Path(raw_output_file).write_text(
        json.dumps(llm.raw_api_responses, indent=2),
        encoding="utf-8",
    )
    print(f"Saved exact NVIDIA API JSON -> {raw_output_file}")


if __name__ == "__main__":
    run_task(
        "Fix Unsatisfied Requirement",
        "Inspect the rover model, find which requirement is unsatisfied, link it to a valid matching part, and confirm the candidate passes validation.",
        "raw_repair_responses.json",
    )
    run_task(
        "Unanswerable Question (No-Evidence Test)",
        "What is the total mass in kilograms of the rover battery P-BAT?",
        "raw_no_evidence_responses.json",
    )