#!/usr/bin/env python3
"""CLI. Usage:
    export ANTHROPIC_API_KEY=...           # real provider (key comes from the environment only)
    python run_teacher.py
    python run_teacher.py --provider fake  # no key, no network: exercises the whole pipeline
"""
import argparse
import json
import sys
from pathlib import Path

from teacher_intent.client import AnthropicProvider, FakeProvider, ProviderError, ProviderResponse
from teacher_intent.config import SCHEMA_VERSION, load_config
from teacher_intent.runner import run_one


def _fake_behavior(system: str, user: str) -> ProviderResponse:
    intent = {
        "schema_version": SCHEMA_VERSION, "intent": "create_project",
        "title": "Synthetic demo intent", "summary": "Canned output from the fake provider.",
        "components": [{"name": "core", "responsibility": "Does the main job"}],
        "acceptance_criteria": ["Works on the synthetic example"], "constraints": [],
        "risk_flags": ["none"],
    }
    return ProviderResponse(json.dumps(intent), {"input_tokens": 420, "output_tokens": 160}, "fake-teacher-0")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider", choices=["anthropic", "fake"], default="anthropic")
    ap.add_argument("--requests", default="synthetic_requests.json")
    ap.add_argument("--log", default="runs.jsonl")
    args = ap.parse_args(argv)

    cfg = load_config(args.provider)
    try:
        provider = (AnthropicProvider(cfg.model_id, cfg.timeout_s, cfg.max_tokens)
                    if args.provider == "anthropic" else FakeProvider(_fake_behavior))
    except ProviderError as e:
        print(f"setup error: {e}", file=sys.stderr)
        return 2

    requests = json.loads(Path(args.requests).read_text(encoding="utf-8"))
    failures = 0
    with open(args.log, "a", encoding="utf-8") as log:
        for req in requests:
            rec = run_one(req, provider, cfg)
            log.write(json.dumps(rec) + "\n")
            cost = rec["estimated_cost_usd"]
            print(f"{rec['request_id']:<10} {rec['status']:<17} {rec['duration_s']:>7.2f}s  "
                  f"usage={rec['usage']}  est_cost=${cost if cost is not None else 'n/a'}"
                  + (f"  [{rec['error_detail']}]" if rec["error_detail"] else ""))
            failures += rec["status"] != "ok"
    print(f"\nmodel={cfg.model_id} provider={args.provider} log={args.log}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
