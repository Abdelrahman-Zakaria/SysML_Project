import argparse
import json
import os
import sys

from .cost import load_pricing
from .providers import AnthropicProvider, ConfigError, FakeProvider
from .runner import request_intent


def main(argv=None):
    p = argparse.ArgumentParser(prog="intent_teacher", description=__doc__)
    p.add_argument("--provider", choices=["anthropic", "fake"], default="anthropic")
    p.add_argument("--model", default=os.environ.get("TEACHER_MODEL"),
                   help="teacher model ID (or set TEACHER_MODEL); required for anthropic")
    p.add_argument("--fake-mode", default="ok",
                   choices=["ok", "malformed", "bad_json", "timeout", "provider_error"])
    src = p.add_mutually_exclusive_group()
    src.add_argument("--example", help="id from examples/requests.json", default="library-checkout")
    src.add_argument("--request", help="free-text synthetic request")
    p.add_argument("--examples-file", default="examples/requests.json")
    p.add_argument("--timeout", type=float, default=30.0)
    p.add_argument("--pricing", default="pricing.json")
    p.add_argument("--log", default="runs.jsonl", help="append-only JSONL audit log")
    args = p.parse_args(argv)

    try:
        provider = FakeProvider(args.fake_mode) if args.provider == "fake" else AnthropicProvider(args.model)
        if args.request:
            text = args.request
        else:
            with open(args.examples_file, encoding="utf-8") as fh:
                text = next(e["request"] for e in json.load(fh) if e["id"] == args.example)
        pricing = load_pricing(args.pricing) if os.path.exists(args.pricing) else None
    except (ConfigError, StopIteration, OSError) as exc:
        print(f"config error: {exc}", file=sys.stderr)
        return 2

    record = request_intent(provider, text, timeout=args.timeout, pricing=pricing).to_dict()
    with open(args.log, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record) + "\n")
    print(json.dumps(record, indent=2))
    return 0 if record["status"] == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
