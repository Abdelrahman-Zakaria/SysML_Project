# AI-Powered Project Intent Extraction

## 1. Project Overview

This project is a Python-based AI application that analyzes graduation project requests and converts them into structured, versioned JSON intents.

The application sends a project request to an AI model, receives its response, validates the generated JSON locally using Pydantic, and records execution metadata.

**The objective is to extract and structure project requirements, not to generate or execute source code.**

### Why NVIDIA Instead of Hugging Face?

During development, we initially explored using Hugging Face inference providers. However, we encountered difficulties obtaining model responses with the available free access and provider availability.

We therefore selected **NVIDIA NIM**, which provided a working inference endpoint for our selected model during development.

We use NVIDIA's OpenAI-compatible API endpoint, allowing us to communicate with the model through the OpenAI Python SDK.

This was a practical choice based on our testing experience, not a claim that Hugging Face is exclusively a paid service.

## 2. Technologies Used

- Python
- NVIDIA NIM API
- OpenAI Python SDK
- Pydantic
- Pytest
- HTTPX
- JSON

## 3. Project Architecture

The application follows this execution pipeline:

1. **Project Request:** Prepare a synthetic graduation project request.
2. **Prompt Construction:** Build the messages using a predefined system prompt.
3. **AI Inference:** Send the request to the NVIDIA-hosted model.
4. **Response Extraction:** Extract the generated JSON response and API usage information.
5. **Local Validation:** Validate the response against the predefined Pydantic schema.
6. **Metadata Recording:** Record model information, prompt version, execution duration, token usage, and execution status.
7. **Logging:** Save execution records locally.

### Main Components

| File | Responsibility |
|---|---|
| `config.py` | Loads API credentials and model configuration from environment variables. |
| `schemas.py` | Defines the expected JSON structure using Pydantic. |
| `prompts.py` | Contains the system prompt, prompt version, and message builder. |
| `inference.py` | Handles communication with NVIDIA and extracts response information. |
| `validator.py` | Validates the generated JSON against the project schema. |
| `main.py` | Coordinates the complete application workflow. |

## 4. Project Structure

```text
LAB_2/
│
├── src/
│   ├── __init__.py
│   ├── config.py
│   ├── schemas.py
│   ├── prompts.py
│   ├── inference.py
│   ├── validator.py
│   └── main.py
│
├── tests/
│   ├── test_validator.py
│   └── test_inference.py
│
├── .gitignore
├── requirements.txt
└── README.md
```

The `logs/` directory is generated automatically when the application runs. It contains execution records and is excluded from Git.

## 5. JSON Intent Schema

The application expects the AI model to return a JSON object containing exactly these fields:

| Field | Description |
|---|---|
| `schema_version` | Version of the JSON schema. |
| `project_name` | Name of the graduation project. |
| `project_type` | Project category: embedded, software, AI, or other. |
| `main_components` | Main hardware and software components. |
| `objectives` | Main objectives of the project. |

Pydantic enforces the schema using:

- `extra="forbid"` to reject unexpected fields.
- `strict=True` to prevent unwanted type coercion.
- Field constraints to enforce required values and valid lengths.
- Enum validation to restrict project categories.

Invalid JSON or responses that do not match the schema are rejected locally.

## 6. Installation and Setup

### Prerequisites

- Python 3.10 or later.
- An NVIDIA API key.
- Internet connection.

### Create a virtual environment

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### Install dependencies

```powershell
python -m pip install -r requirements.txt
```

## 7. Environment Configuration

The application uses environment variables to protect API credentials.

Configure the following variables in PowerShell:

```powershell
$env:NVIDIA_API_KEY="your_actual_nvidia_api_key"
$env:MODEL_ID="nvidia/nemotron-3.5-super-vl-120b-a12b"
```

These variables are available only in the current PowerShell session unless configured permanently.

Each developer must provide their own API key.

**Never hardcode API keys in source files or upload them to GitHub.**

## 8. Running the Application

From the project root, execute:

```powershell
python -m src.main
```

The application will:

- Send a synthetic Smart Parking System request.
- Receive a structured response from NVIDIA.
- Validate the JSON response.
- Display the extracted project intent.
- Display execution metadata.
- Save the execution record in `logs/execution_log.jsonl`.

## 9. Execution Metadata

For each execution, the application records:

| Metadata | Description |
|---|---|
| Timestamp | Execution date and time in UTC. |
| Provider | NVIDIA. |
| Model ID | Selected AI model. |
| Prompt version | Version of the system prompt. |
| Duration | API execution time in seconds. |
| Input tokens | Number of input tokens. |
| Output tokens | Number of generated tokens. |
| Total tokens | Total token usage. |
| Status | Success or failure. |

Token usage is obtained from the API response when available.

**Cost estimation is not implemented yet.** It will require verified model pricing and a calculation based on input and output token usage.

## 10. Automated Testing

The project uses Pytest to verify response validation and inference behavior.

Run all tests:

```powershell
pytest -v
```

### Current Test Coverage

**JSON validation tests:**

- Valid JSON acceptance.
- Malformed JSON rejection.
- Missing required fields.
- Invalid project category.
- Incorrect data types.
- Unexpected fields.

**Inference tests:**

- Successful inference simulation.
- Connection error handling.
- Provider error handling.

Inference tests use mocks to simulate API responses and errors. They do not make actual NVIDIA API calls or consume API credits.

The current test suite contains nine tests.

## 11. Updating Dependencies

If you install additional packages or change dependency versions, update `requirements.txt` using:

```powershell
python -m pip freeze > requirements.txt
```

This records the installed packages and their versions so another developer can reproduce the environment.

After updating dependencies, run:

```powershell
pytest -v
```

## 12. Security and Data Handling

- API keys are loaded from environment variables.
- Virtual environments are excluded from Git.
- Python cache files are excluded from Git.
- Execution logs are excluded from Git.
- Synthetic project requests are used for testing.
- No real or confidential project information should be submitted without authorization.