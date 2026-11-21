# AIWeek3 Lab

This lab builds a small, inspectable agent for elevator-model inspection. The
model proposes a named tool and typed arguments. Python validates both, executes
only allow-listed tools, and returns observable evidence or an explicit failure.
Model-generated prose is never accepted as engineering evidence.

## Agent loop

1. Record the user request.
2. Give the model the available tools, descriptions, and JSON argument schemas.
3. Validate the proposed tool call and arguments.
4. Execute the matching deterministic tool or configured SysML validator.
5. Return evidence, rejection, missing evidence, timeout, or tool failure.

The default limits are three model/tool calls and ten seconds total runtime.
The remaining time is passed to the decision provider; the live provider uses
that value as the `InferenceClient` timeout. The configured validator also gets
only the remaining time. Provider exceptions and tool exceptions become
non-success results. Ctrl+C or EOF during input and Ctrl+C during a run are
reported as cancellation.

## Tools

- `list_available_items` lists local parts or requirement IDs.
- `get_metadata` reads deterministic local metadata.
- `check_condition` evaluates one of the supported local conditions.
- `propose_requirement` builds a typed SysML v2 requirement candidate and asks
  the configured validator to check it. A passing candidate is returned as
  `requires_review`; it is never written into the project model automatically.

The first three tools use local elevator facts. For proposals, the validator
must be configured explicitly. `SYSML_VALIDATOR` must point to a local wrapper
that accepts one `.sysml` file path as its sole argument, invokes the installed
SysML v2 compiler or official validator, and returns exit code 0 only when the
candidate passes validation. A nonzero exit code is a rejected tool result. If
no validator is configured or it cannot run, the proposal fails closed and is
not presented as validated. The lab does not claim that a lightweight text
check is equivalent to a SysML compiler.

## Setup

Week 3 has its own virtual environment and dependencies:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

For live model calls, set `BASE_URL`, `API_KEY`, and `MODEL_ID` in `.env`. Set
`SYSML_VALIDATOR` to your local validator wrapper to enable requirement
proposals. Keep `.env` and API keys out of version control. The deterministic
tests do not need a model API key or an installed SysML validator.

```powershell
.\venv\Scripts\python.exe app.py
```

## Rejection-path exercises

The tests cover successful deterministic inspection, fabricated tool names,
invalid arguments, missing evidence, fabricated unsupported claims, malformed
model output, provider and tool exceptions, runtime and call limits, ambiguous
requests, cancellation, missing validator configuration, validator rejection,
and a validated proposal awaiting human review.

Run the tests with:

```powershell
.\venv\Scripts\python.exe -m pytest -q
```
