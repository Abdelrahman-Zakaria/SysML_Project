import os
from typing import Any
from pathlib import Path

from dotenv import load_dotenv
from huggingface_hub import InferenceClient

from config import (
    API_KEY_ENV_VAR,
    INFERENCE_PROVIDER,
    MAX_OUTPUT_TOKENS,
    MAX_RETRY_ATTEMPTS,
    MODEL_ID,
    REQUEST_TIMEOUT_SECONDS,
)
from structured_output import build_response_format
from reliability import call_with_retry

ENV_FILE = Path(__file__).with_name(".env")
load_dotenv(ENV_FILE)


def create_client() -> InferenceClient:
    """Create an authenticated inference client."""

    api_key = os.getenv(API_KEY_ENV_VAR)

    if not api_key:
        raise RuntimeError(
            f"Missing API key. Set {API_KEY_ENV_VAR} in .env."
        )

    return InferenceClient(
        model=MODEL_ID,
        provider=INFERENCE_PROVIDER,
        api_key=api_key,
        timeout=REQUEST_TIMEOUT_SECONDS
    )


def generate_response(messages: list[dict[str, str]]) -> Any:
    """Send messages and request structured JSON output."""

    if not messages:
        raise ValueError("Messages cannot be empty.")

    client = create_client()

    response = call_with_retry(
        lambda: client.chat_completion(
            messages=messages,
            response_format=build_response_format(),
            max_tokens=MAX_OUTPUT_TOKENS,
        ),
        max_attempts=MAX_RETRY_ATTEMPTS,
    )

    return response
