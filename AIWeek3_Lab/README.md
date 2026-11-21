# AIWeek3 Lab

This lab implements a small, inspectable agent for SysML elevator inspection.
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

Week 3 has its own virtual environment and dependencies:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

For an optional live run, create `.env` from `.env.example` and set your own
OpenAI-compatible provider URL, API key, and model ID. Any provider is suitable
if its endpoint supports the chat-completion interface used by
`huggingface_hub.InferenceClient`. Do not commit `.env` or an API key. Offline
tests do not require an API key.

```powershell
Copy-Item .env.example .env
.\venv\Scripts\python.exe app.py
```

Run tests with:

```powershell
.\venv\Scripts\python.exe -m pytest -q
```

## Exit-gate demonstrations

- Replace the model's tool name with `invent_fact`: the result is rejected.
- Omit a required argument: the result is rejected.
- Request an unknown component: the result is `no_evidence`.
- Return a fabricated claim from the model: it cannot become a successful
  engineering result because only tool observations are accepted.
