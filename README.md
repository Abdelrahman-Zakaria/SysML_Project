# Week 2 Lab: LLM-Based Engineering Intent Extraction

## 1. Project Overview

This project converts a natural-language engineering system description into a structured, versioned JSON intent.

The application uses Google Gemini to extract:

- System name and type
- System description
- Main components
- Functional requirements
- Performance requirements
- System constraints

The generated JSON is validated locally before being accepted.

The application does not generate executable code.

## 2. Architecture

The application follows this pipeline:

1. User provides a natural-language engineering description.
2. The prompt builder creates a structured extraction prompt.
3. Google Gemini generates a JSON response.
4. The JSON parser checks whether the response is valid JSON.
5. Pydantic validates the JSON structure and field constraints.
6. Semantic validation checks engineering-intent consistency.
7. The validated intent and execution information are displayed.

## 3. Technology Stack

- Python
- Google Gemini API
- google-genai
- Pydantic
- python-dotenv
- Tenacity
- HTTPX
- Pytest

## 4. Model and Provider

- Provider: Google Gemini
- Model ID: Configured through `GEMINI_MODEL` in `.env`
- Selected model: `gemini-3.6-flash`
- Prompt Version: `1.0`
- Pricing Tier: Free Tier

The model ID and API key are configured through environment variables, so users do not need to edit the source code to configure them.

## 5. Cost Assumptions

This project is configured to use the Google Gemini API Free Tier.

The application reports an estimated API token cost of `$0.00` when `GEMINI_PRICING_TIER=free`.

This assumes the selected model and requests are eligible for Free Tier usage and remain within Google's applicable limits and terms.

Token usage information is recorded when returned by the provider. Token counts are usage information and do not necessarily indicate billable usage.

Official pricing information:

https://ai.google.dev/gemini-api/docs/pricing

## 6. Reliability and Error Handling

The application handles:

- Request timeouts
- Temporary provider errors
- Rate limits
- Invalid JSON responses
- Schema validation errors
- Semantic validation errors

Transient API errors are retried up to three attempts using exponential backoff.

Permanent errors are not retried.

## 7. Setup

### Requirements

Python 3.10 or later.

### Create a virtual environment

```bash
python -m venv .venv
```

Activate it on Windows:

```bash
.venv\Scripts\activate
```

### Install dependencies

```bash
pip install -r requirements.txt
```

### Configure environment variables

Create a `.env` file in the project root:

```env
GEMINI_API_KEY=your_api_key_here
GEMINI_MODEL=gemini-3.6-flash
GEMINI_PRICING_TIER=free
```

Never commit the `.env` file or expose your API key.

The API key must be obtained by each user from Google AI Studio and stored locally in their own `.env` file.

## 8. Run the Application

```bash
python main.py
```

## 9. Run Tests

```bash
python -m pytest -v
```

The automated tests cover:

- Valid and invalid schema data
- Invalid system types and schema versions
- Empty requirements
- Invalid requirement types
- Missing required fields
- Unexpected fields
- Duplicate components
- Duplicate components with different capitalization or whitespace
- Valid JSON objects
- Malformed JSON responses
- JSON arrays instead of JSON objects
- Empty responses

## 10. Current Verification Status

The following have been verified:

- Live Gemini API request completed successfully.
- Gemini returned a valid JSON response.
- JSON parsing completed successfully.
- Pydantic schema validation passed.
- Semantic validation passed.
- All 14 automated local tests passed.

The successful live test returned HTTP 200 OK and demonstrated the complete natural-language-to-validated-JSON workflow.

Live generation still depends on API availability, valid credentials, and applicable Free Tier limits.