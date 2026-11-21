# Week 2 LLM Lab: SysML Requirements Chatbot

A terminal chatbot that turns natural-language engineering requests into a
**validated, structured Intent**, and shows it as a readable answer.
Model: `openai/gpt-oss-20b` via `groq`, using Hugging Face `InferenceClient`.
The model produces a structured Intent only, never executable code.

## What it does

- Drafts functional / non-functional requirements ("The X shall ...").
- Asks a clarification question when the request is unclear; your next
  message is treated as the answer (the previous turns are sent as context).
- Marks out-of-scope requests (e.g. "write Python code") as `unsupported`.
- Keeps the validated Intent JSON internally; `/json` shows it.
- Sends at most the last `MAX_HISTORY_MESSAGES` (default 10) messages.
- Never crashes on empty input, API errors or bad model output.

## Install

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows   (Linux/macOS: source .venv/bin/activate)
pip install -r requirements.txt
```

## Configure the API key

Copy `.env.example` to `.env` and set the existing variable:

```
GROQ_API_KEY=your_groq_api_key_here
```

Never commit or submit `.env`. Optional settings (also in `.env`):
`MAX_OUTPUT_TOKENS` (default 2000; gpt-oss spends tokens on reasoning, so
too small a value truncates the JSON), `MAX_HISTORY_MESSAGES` (default 10).

## Run

```bash
python main.py
```

| Command  | Action                                   |
|----------|------------------------------------------|
| `/help`  | Show commands and examples               |
| `/clear` | Clear the conversation                   |
| `/json`  | Show the latest validated Intent as JSON |
| `/exit`  | Close the chatbot (Ctrl+C also works)    |

`python live_demo.py ["request"]` runs a single request and prints the
Intent and run metadata.

## Example session

```
You> Draft a functional requirement for an elevator that stops at the floor selected by the passenger.

Bot> Intent: draft_requirement
Requirement type: functional
Requirement: The elevator shall stop at the floor selected by the passenger.
Clarification needed: No

You> Write a requirement for the brakes.

Bot> Intent: draft_requirement
Requirement type: unspecified
Clarification needed: Yes
Question: What should the brakes do, and under what conditions?

You> They must stop the car within 40 m.

Bot> Intent: draft_requirement
Requirement type: functional
Requirement: The brakes shall stop the vehicle within 40 m.
Clarification needed: No

You> Write Python code to sort a list.

Bot> Intent: unsupported
Sorry, that request is outside what I can do. I only help draft SysML /
engineering requirements ...
```

## How structured output and validation work

1. `prompts.py` builds the messages (system prompt with rules and examples,
   earlier turns, the new request).
2. `structured_output.py` converts the Pydantic `Intent` model into a strict
   JSON Schema, so the provider is asked to return exactly those fields.
3. `llm_client.py` calls the model with retries (`reliability.py`): timeouts,
   HTTP 429/498/500/502/503/504 and connection errors are retried with
   backoff; `Retry-After` is honoured but capped at 30 s.
4. `intent_service.py` checks the reply: no choices, `finish_reason="length"`
   (truncated), empty content.
5. `response_handler.py` parses the JSON and validates it with Pydantic
   (`models.py`): fixed enums, no extra fields, and cross-field rules
   (clarification flag vs. question, `unsupported` must carry no requirement
   text, no blank strings).
6. `metadata.py` logs model, tokens, duration, estimated cost and the outcome
   (`passed`, `failed`, `api_error`) to `logs/usage.jsonl`.

`chat.py` holds the conversation (`ChatSession`) and `main.py` the terminal loop.

## Tests

```bash
python -m pytest -q
```

All tests are offline: the API client is mocked and no real key is needed.
