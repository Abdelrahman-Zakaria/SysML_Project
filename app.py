
import os
import json
import logging
import time

from pathlib import Path
from dataclasses import dataclass
from typing import Literal

from dotenv import load_dotenv
from groq import Groq
from httpx import TimeoutException
from pydantic import BaseModel, ConfigDict, Field, ValidationError

CONFIDENCE_THRESHOLD = 0.70
# 1. Project configuration

BASE_DIR = Path(__file__).resolve().parent

load_dotenv(BASE_DIR / ".env")

MODEL_ID = os.getenv("MODEL_ID", "openai/gpt-oss-120b")
PROMPT_VERSION = os.getenv("PROMPT_VERSION", "intent-v1")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

SYSTEM_PROMPT = """
You are a software project intent extractor.

Task:
Extract the user's software project request into a structured intent.

Allowed actions:
- create
- update
- explain

Allowed project types:
- web_application
- mobile_application
- desktop_application
- api
- other

Output contract:
Return ONLY valid JSON with this structure:

{
  "schema_version": "1.0",
  "intent": {
    "action": "create",
    "project_type": "web_application",
    "description": "Short project description",
    "features": ["feature 1", "feature 2"]
    "confidence": 0.85
  }
}
Confidence:
- Include a confidence score between 0.0 and 1.0.
- Higher values indicate stronger confidence in the extracted intent.
- Lower values indicate ambiguity or missing information.
- Do not use high confidence when the request is unclear.

Constraints:
- Never generate executable code.
- Never invent requirements that are not present in the request.
- Keep the description concise.
- Include only clearly requested features.
- Do not include additional JSON fields.
- If the request is unclear, do not guess its meaning.
- Confidence represents the model's estimated certainty about the extracted intent.
- Use lower confidence for ambiguous or incomplete requests.
- Never invent missing requirements.
"""
# 2. Load system prompt
def load_prompt():
    return SYSTEM_PROMPT


# 3. Configure logging

logging.basicConfig(
    filename=str(BASE_DIR / "app.log"),
    level=logging.INFO,
    format="%(message)s"
)

logger = logging.getLogger(__name__)


# 4. Define expected output schema

class ProjectIntent(BaseModel):

    model_config = ConfigDict(
        extra="forbid",
        strict=True
    )

    action: Literal[
        "create", "update", "explain", "analyze"
    ]

    project_type: Literal[
        "web_application",
        "mobile_application",
        "desktop_application",
        "api",
        "other"
    ]

    description: str = Field(
        min_length=1,
        max_length=300
    )

    features: list[str] = Field(max_length=10)

    confidence: float = Field(
        ge=0.0,
        le=1.0
    )

class IntentResponse(BaseModel):

    model_config = ConfigDict(
        extra="forbid",
        strict=True
    )

    schema_version: Literal["1.0"]
    intent: ProjectIntent


# 5. Provider result structure

@dataclass
class ProviderResult:
    text: str
    usage: dict | None = None


class ProviderError(Exception):
    pass


# 6. Mock provider (used for testing)

def generate_mock_response(
    request: str,
    system_prompt: str
) -> ProviderResult:

    print("Using Mock Provider...")

    mock_output = {
        "schema_version": "1.0",
        "intent": {
            "action": "create",
            "project_type": "web_application",
            "description": "Library management system",
            "features": [
                "User login",
                "Book borrowing",
                "Book returns"
            ]
        }
    }

    return ProviderResult(
        text=json.dumps(mock_output),
        usage={
            "input_tokens": 35,
            "output_tokens": 45
        }
    )


# 7. Real Groq provider

def generate_groq_response(
    request: str,
    system_prompt: str
) -> ProviderResult:

    if not GROQ_API_KEY:
        raise ProviderError("Missing Groq API key")

    try:
        client = Groq(
            api_key=GROQ_API_KEY,
            timeout=30
        )

        response = client.chat.completions.create(
            model=MODEL_ID,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": request
                }
            ],
            temperature=0.2,
            max_completion_tokens=1000
        )

        generated_text = response.choices[0].message.content

        if not generated_text:
            raise ProviderError("Empty response from Groq")

        usage = None

        if response.usage:
            usage = {
                "input_tokens": response.usage.prompt_tokens,
                "output_tokens": response.usage.completion_tokens
            }

        return ProviderResult(
            text=generated_text,
            usage=usage
        )

    except TimeoutException as error:
        raise TimeoutError("Groq request timed out") from error

    except ProviderError:
        raise

    except Exception as error:
        raise ProviderError(
            f"Groq request failed: {type(error).__name__}"
        ) from error


# 8. Validate JSON locally

def validate_response(raw_response: str) -> IntentResponse:
    return IntentResponse.model_validate_json(raw_response)


# 9. Estimate API cost

def estimate_cost(usage: dict | None):

    if not usage:
        return None

    input_rate = os.getenv("INPUT_PRICE_PER_MILLION")
    output_rate = os.getenv("OUTPUT_PRICE_PER_MILLION")

    if not input_rate or not output_rate:
        return None

    input_tokens = usage.get("input_tokens")
    output_tokens = usage.get("output_tokens")

    if input_tokens is None or output_tokens is None:
        return None

    try:
        input_rate = float(input_rate)
        output_rate = float(output_rate)

        if input_rate < 0 or output_rate < 0:
            return None

        cost = (
            input_tokens * input_rate
            + output_tokens * output_rate
        ) / 1_000_000

        return round(cost, 8)

    except (ValueError, TypeError):
        return None


# 10. Main request handler

def run_request(
    request: str,
    system_prompt: str = "",
    provider_fn=generate_mock_response
):

    start_time = time.perf_counter()

    usage = None
    result = None
    status = "success"
    error_type = None

    try:
        provider_result = provider_fn(
            request,
            system_prompt
        )

        if not isinstance(provider_result, ProviderResult):
            raise ProviderError(
                "Unexpected provider response format"
            )

        usage = provider_result.usage

        result = validate_response(
            provider_result.text
        )
        if result.intent.confidence < CONFIDENCE_THRESHOLD:
         print("Warning: Low confidence. Clarification may be needed.")

    except TimeoutError:
        status = "failed"
        error_type = "timeout"

    except ValidationError as error:
        status = "rejected"
        error_type = "invalid_output"

        print("\nValidation Error Details:")
        print(error)

        if "provider_result" in locals():
            print("\nRaw Model Response:")
            print(provider_result.text)

    except ProviderError:
        status = "failed"
        error_type = "provider_error"

    except Exception:
        status = "failed"
        error_type = "provider_error"

    duration = round(
        time.perf_counter() - start_time,
        4
    )

    metadata = {
        "model_id": MODEL_ID,
        "prompt_version": PROMPT_VERSION,
        "duration_seconds": duration,
        "token_usage": usage,
        "estimated_cost": estimate_cost(usage),
        "status": status,
        "error_type": error_type
    }

    logger.info(json.dumps(metadata))

    return {
        "result": result,
        "metadata": metadata
    }


# 11. Main application


def main():

    print("Project Intent Extractor")
    print("------------------------")

 

    # Get request from user
    print("\nEnter your project request:")
    project_request = input("> ").strip()

    if not project_request:
        print("Error: Request cannot be empty.")
        return

    print("\nSending request to Groq...")

    response = run_request(
        project_request,
        SYSTEM_PROMPT,
        provider_fn=generate_groq_response
)

    if response["result"] is not None:

        print("\nValidated Intent:")

        print(
            response["result"].model_dump_json(indent=2)
        )

    else:
        print("\nRequest rejected or failed.")

    print("\nMetadata:")
    print(json.dumps(response["metadata"], indent=2))

    print("\nLog saved to app.log")


if __name__ == "__main__":
    main()
