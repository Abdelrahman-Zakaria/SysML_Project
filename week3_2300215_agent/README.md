# Week 3: Safe SysML Tool-Calling Agent

A bounded tool-calling agent for querying and validating mock SysML v2 elements (`REQ-101`, `BLK-204`) with Pydantic schema validation, allowlisted tool execution, and offline exit-gate tests.

## 1. Setup

From the repository root (`SysML_Project`), create and activate a virtual environment, then install the dependencies:

```bash
python -m venv .venv

# Fish shell:
source .venv/bin/activate.fish

# Bash / Zsh:
source .venv/bin/activate

pip install -r week3_2300215_agent/requirements.txt
```

## 2. Configure Environment Variables

Copy `.env.example` to `.env` in the repository root and add your Gemini API key:

```bash
cp week3_2300215_agent/.env.example .env
```

Edit `.env`:
```env
BASE_URL=[https://generativelanguage.googleapis.com/v1beta/openai/](https://generativelanguage.googleapis.com/v1beta/openai/)
GEMINI_API_KEY=your_gemini_api_key_here
MODEL_ID=gemini-3.5-flash-lite
```

## 3. Run Offline Unit Tests

Runs the 5 exit-gate tests (unknown tools, invalid arguments, missing elements, tool crashes, and valid runs) without making API calls:

```bash
python -m unittest week3_2300215_agent.test_agent -v
```

## 4. Run the Live Agent

Starts the interactive CLI backed by `gemini-3.5-flash-lite`:

```bash
python -m week3_2300215_agent.agent
```

Example prompts:
- `List all elements and check if BLK-204 can weigh 48 kg.`
- `Inspect element REQ-999.`