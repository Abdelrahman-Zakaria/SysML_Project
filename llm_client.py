
import os
import time
import logging
import httpx

from dataclasses import dataclass
from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.genai.errors import APIError
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception,
    before_sleep_log
)

load_dotenv()

# --------------------------------------------------
# Configuration
# --------------------------------------------------

API_KEY = os.getenv("GEMINI_API_KEY")
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")

# Prices are USD per one million tokens.
# Leave them unset until verified from official pricing.
PRICING_TIER = os.getenv("GEMINI_PRICING_TIER", "free").strip().lower()

INPUT_PRICE = os.getenv(
    "GEMINI_INPUT_PRICE_PER_MILLION", ""
).strip() or None

OUTPUT_PRICE = os.getenv(
    "GEMINI_OUTPUT_PRICE_PER_MILLION", ""
).strip() or None

if not API_KEY:
    raise RuntimeError("GEMINI_API_KEY is missing from .env")

client = genai.Client(
    api_key=API_KEY,
    http_options=types.HttpOptions(timeout=60000)
)

# --------------------------------------------------
# Logging
# --------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("app.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# --------------------------------------------------
# Result structure
# --------------------------------------------------

@dataclass
class LLMResult:
    text: str
    provider: str
    model_id: str
    prompt_version: str
    duration_seconds: float
    input_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None
    estimated_cost_usd: float | None


# --------------------------------------------------
# Retry configuration
# --------------------------------------------------


def is_retryable_error(exc):

    if isinstance(exc, (TimeoutError, httpx.TimeoutException)):
        return True

    if isinstance(exc, APIError):

        if exc.code == 429:
            error_message = str(exc).lower()

            # Do not retry when the daily quota is exhausted.
            daily_quota_indicators = [
                "per day limit exceeded",
                "generaterequestsperday",
            ]

            if any(
                indicator in error_message
                for indicator in daily_quota_indicators
            ):
                return False

            # Other 429 errors may be temporary.
            return True

        return exc.code in {408, 500, 502, 503, 504}

    return False



@retry(
    retry=retry_if_exception(is_retryable_error),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=4),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True
)
def send_request(prompt: str):
    logger.info("Sending request to Gemini")
    return client.models.generate_content(
        model=MODEL,
        contents=prompt
    )


# --------------------------------------------------
# Usage and cost helpers
# --------------------------------------------------

def get_token_count(usage, field):
    if usage is None:
        return None

    value = getattr(usage, field, None)

    if value is None:
        return None

    return int(value)


def estimate_cost(input_tokens, output_tokens):

    if PRICING_TIER == "free":
        return 0.0

    if input_tokens is None or output_tokens is None:
        return None

    if INPUT_PRICE is None or OUTPUT_PRICE is None:
        return None

    try:
        input_rate = float(INPUT_PRICE)
        output_rate = float(OUTPUT_PRICE)

    except ValueError:
        logger.warning("Invalid token pricing configuration.")
        return None

    input_cost = input_tokens * input_rate / 1_000_000
    output_cost = output_tokens * output_rate / 1_000_000

    return input_cost + output_cost

# --------------------------------------------------
# Main generation function
# --------------------------------------------------

def generate_text(prompt: str, prompt_version: str) -> LLMResult:

    if not prompt.strip():
        raise ValueError("Prompt cannot be empty")

    start_time = time.perf_counter()

    try:
        response = send_request(prompt)

    except Exception:
        duration = time.perf_counter() - start_time

        logger.error(
            "Gemini request failed after %.2f seconds",
            duration
        )

        raise

    duration = time.perf_counter() - start_time

    if not response.text:
        raise RuntimeError("Gemini returned an empty response")

    usage = getattr(response, "usage_metadata", None)

    input_tokens = get_token_count(usage, "prompt_token_count")
    output_tokens = get_token_count(usage, "candidates_token_count")
    total_tokens = get_token_count(usage, "total_token_count")

    estimated_cost = estimate_cost(
        input_tokens,
        output_tokens
    )

    result = LLMResult(
        text=response.text,
        provider="Google Gemini",
        model_id=MODEL,
        prompt_version=prompt_version,
        duration_seconds=duration,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        estimated_cost_usd=estimated_cost
    )

    logger.info("Request completed successfully")
    logger.info("Provider: %s", result.provider)
    logger.info("Model ID: %s", result.model_id)
    logger.info("Prompt version: %s", result.prompt_version)
    logger.info("Response time: %.2f seconds", duration)
    logger.info("Input tokens: %s", input_tokens)
    logger.info("Output tokens: %s", output_tokens)
    logger.info("Total tokens: %s", total_tokens)
    logger.info("Estimated cost (USD): %s", estimated_cost)

    return result
