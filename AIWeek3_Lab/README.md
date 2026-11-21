# AIWeek3 Lab

This lab extends the Week 2 intent classifier into a small, inspectable agent.
The model may propose one typed tool call, but ordinary Python code validates
the tool name and arguments and executes the tool against deterministic local
elevator data.

## Design

`run_agent` implements:

1. user request
2. model decision
3. Pydantic validation and allow-list checking
4. deterministic tool execution
5. observable result or explicit failure

The loop has call and runtime limits. It never treats model text as engineering
evidence. Unknown tools, invalid arguments, missing evidence, malformed model
output, and tool failures are non-success outcomes.

Available tools:

- `list_available_items`
- `get_metadata`
- `check_condition`

## Setup

Use the existing Week 2 environment and dependencies:

```powershell
..\AIWeek2_Lab\venv\Scripts\python.exe -m pytest -q
```

For an optional live run, copy the Week 2 `.env` values into this lab's
environment. Reuse the same `BASE_URL`, `GEMINI_API_KEY`, and `MODEL_ID`; do not
commit `.env` or an API key. Offline tests do not require an API key.

```powershell
Copy-Item ..\AIWeek2_Lab\.env .env
..\AIWeek2_Lab\venv\Scripts\python.exe app.py
```

## Exit-gate demonstrations

- Replace the model's tool name with `invent_fact`: the result is rejected.
- Omit a required argument: the result is rejected.
- Request an unknown component: the result is `no_evidence`.
- Return a fabricated claim from the model: it cannot become a successful
  engineering result because only tool observations are accepted.
