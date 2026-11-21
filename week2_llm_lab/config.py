"""Central configuration for the Week 2 LLM lab."""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env here so every setting below can be overridden from it.
load_dotenv(Path(__file__).with_name(".env"))

MODEL_ID = "openai/gpt-oss-20b"

# inference provider
INFERENCE_PROVIDER = "groq"

# Name of the environment variable containing the API key
API_KEY_ENV_VAR = "GROQ_API_KEY"


def _int_from_env(name: str, default: int) -> int:
    """Read a positive integer setting from the environment."""

    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return value if value > 0 else default


# Output-token budget. gpt-oss is a reasoning model, so reasoning tokens
# count against this limit; 500 was too small. Override with MAX_OUTPUT_TOKENS.
MAX_OUTPUT_TOKENS = _int_from_env("MAX_OUTPUT_TOKENS", 2000)

# Request timeout in seconds.
REQUEST_TIMEOUT_SECONDS = _int_from_env("REQUEST_TIMEOUT_SECONDS", 60)

# Retry policy for temporary API / network failures.
MAX_RETRY_ATTEMPTS = 3
MAX_RETRY_DELAY_SECONDS = 30.0

# Chat history sent to the model: at most this many messages
# (one turn = one user message + one assistant message).
MAX_HISTORY_MESSAGES = _int_from_env("MAX_HISTORY_MESSAGES", 10)
