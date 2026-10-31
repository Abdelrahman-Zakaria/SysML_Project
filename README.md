# Teacher-intent harness

Sends a **synthetic** project request to a teacher model, expects a versioned JSON **intent**
(`intent.v1`, data only, never code), validates it locally, and logs one JSON line per run.

## Run (no source edits, no secrets in files)

    python3 -m unittest -v                       # 34 tests, no network, no key
    python3 run_teacher.py --provider fake       # whole pipeline, no key, no network
    export ANTHROPIC_API_KEY=...                 # key lives only in your shell
    python3 run_teacher.py                       # real teacher; appends to runs.jsonl

Requires Python 3.10+, stdlib only. A missing key exits with code 2 before any network call.

## Selected model / provider and why

- **Provider:** Anthropic Messages API. **Default model:** `claude-sonnet-5-5`
  (override: `TEACHER_MODEL_ID`).
- Rationale: a mid-tier model is the usual cost/quality balance for a *teacher* that emits
  short structured output. Swap in any other model ID without code changes; to change the
  provider, add a class with `.name` and `.complete(system, user)` in `client.py`.
- Temperature is 0 for repeatability. Timeout default 30 s (`TEACHER_TIMEOUT_S`).

## Cost assumptions (must be confirmed)

    estimated_cost_usd = input_tokens/1e6 * PRICE_IN + output_tokens/1e6 * PRICE_OUT

- Defaults: **$3.00 / Mtok input, $15.00 / Mtok output** (`TEACHER_PRICE_IN_PER_MTOK`,
  `TEACHER_PRICE_OUT_PER_MTOK`). These are assumptions, **not fetched from the provider**.
  Check the current pricing page and set the env vars if they differ.
- Token counts come from the provider's `usage` field. If it is absent, cost is `null`
  (never guessed). Tokens are costed even when the output is later rejected.
- Excludes batch/caching discounts, retries, and taxes.

## Failure handling (each recorded with `status`)

| status | cause |
|---|---|
| `ok` | valid `intent.v1` |
| `timeout` | no response within the timeout |
| `provider_error` | HTTP error, network error, bad envelope, missing key |
| `invalid_json` | output is not a JSON document (markdown-fenced JSON is rejected on purpose) |
| `schema_violation` | wrong version/type/enum/size, extra or missing fields, or code-like content |

The code-like check is a heuristic guard (fences, `def`, `import`, `rm -rf`, ...), not a sandbox.
Nothing in this program executes teacher output.

## Log record fields

`request_id, started_at, provider, model_id, model_id_reported, prompt_version, schema_version,
status, error_type, error_detail, duration_s, usage, estimated_cost_usd, pricing_assumption,
intent, raw_output_excerpt` (excerpt only on rejected output, capped at 500 chars).

## Data policy

`synthetic_requests.json` is fabricated. Only fabricated or approved public examples should be
added. Do not put private or customer data in requests, since they are sent to the provider.
