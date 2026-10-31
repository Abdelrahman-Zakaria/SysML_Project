# AIWeek2 Lab

This project classifies natural-language SysML v2 requests. It sends a request
to a chat model and validates the returned intent with Pydantic.

The classifier returns:

- `generate` when the user wants to create something.
- `validate` when the user wants to check something.
- `extract` when the user wants to retrieve information.

It also identifies the requested target and returns a confidence score.

## Setup

Create a virtual environment, install the dependencies, and copy
`.env.example` to `.env`:

```powershell
python -m venv venv
\venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Set these values in `.env`:

| Variable         | Purpose                                   |
| ---------------- | ----------------------------------------- |
| `BASE_URL`       | OpenAI-compatible inference API URL       |
| `GEMINI_API_KEY` | API key for the inference provider        |
| `MODEL_ID`       | Model identifier accepted by the provider |

Never commit `.env` or a real API key.

## Run

```powershell
.\\venv\Scripts\python.exe app.py
```

Example:

```text
Your request: Check the engine mass

Analyzing intent...

Validated Pydantic Object:
Action: validate
Target: engine mass
Confidence: 0.94
```

The application rejects empty requests and requests longer than 2,000
characters. Press `Ctrl+C` or send EOF to cancel input safely.

## Test

```powershell
.\\venv\Scripts\python.exe -m pytest -q
```

The tests cover Pydantic validation, JSON response cleanup, successful mocked
API responses, invalid model output, missing configuration, and timeouts.
