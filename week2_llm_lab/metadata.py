
"""
Collect inference metadata and estimate API usage cost.
"""

import json
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from config import MODEL_ID, INFERENCE_PROVIDER
from prompts import PROMPT_VERSION


# Published Groq prices for GPT-OSS 20B.
# Prices are USD per 1 million tokens.
INPUT_PRICE_PER_MILLION = Decimal("0.075")
OUTPUT_PRICE_PER_MILLION = Decimal("0.30")

PRICING_CHECKED_ON = "2026-11-20"

PRICING_SOURCE = (
    "https://console.groq.com/docs/model/openai/gpt-oss-20b"
)


def get_token_count(usage, field: str) -> int | None:
    """Read a token count safely from the provider response."""

    value = getattr(usage, field, None)

    if isinstance(value, bool) or not isinstance(value, int):
        return None

    if value < 0:
        return None

    return value


def estimate_cost_usd(
    input_tokens: int | None,
    output_tokens: int | None
) -> float | None:
    """Estimate cost using the published uncached token rates."""

    if input_tokens is None or output_tokens is None:
        return None

    if input_tokens < 0 or output_tokens < 0:
        raise ValueError("Token counts cannot be negative.")

    cost = (
        Decimal(input_tokens) * INPUT_PRICE_PER_MILLION
        + Decimal(output_tokens) * OUTPUT_PRICE_PER_MILLION
    ) / Decimal("1000000")

    rounded_cost = cost.quantize(
        Decimal("0.0000000001"),
        rounding=ROUND_HALF_UP
    )

    return float(rounded_cost)


def build_run_metadata(
    response,
    duration_seconds: float
) -> dict:
    """Build metadata for one completed inference request."""

    if duration_seconds < 0:
        raise ValueError("Duration cannot be negative.")

    usage = getattr(response, "usage", None)

    input_tokens = get_token_count(usage, "prompt_tokens")
    output_tokens = get_token_count(usage, "completion_tokens")
    total_tokens = get_token_count(usage, "total_tokens")

    # Calculate total if the provider did not supply it.
    if total_tokens is None:
        if input_tokens is not None and output_tokens is not None:
            total_tokens = input_tokens + output_tokens

    actual_model = getattr(response, "model", None)

    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "model_id": actual_model or MODEL_ID,
        "provider": INFERENCE_PROVIDER,
        "prompt_version": PROMPT_VERSION,
        "duration_seconds": round(duration_seconds, 4),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "estimated_cost_usd": estimate_cost_usd(
            input_tokens,
            output_tokens
        ),
        "pricing": {
            "input_per_million_usd": str(INPUT_PRICE_PER_MILLION),
            "output_per_million_usd": str(OUTPUT_PRICE_PER_MILLION),
            "basis": "uncached input and output token rates",
            "checked_on": PRICING_CHECKED_ON,
            "source": PRICING_SOURCE
        }
    }


def save_run_metadata(
    metadata: dict,
    log_path: Path | None = None
) -> Path:
    """Append one metadata record to a JSON Lines log."""

    if log_path is None:
        log_path = Path(__file__).parent / "logs" / "usage.jsonl"

    log_path.parent.mkdir(parents=True, exist_ok=True)

    with log_path.open("a", encoding="utf-8") as file:
        file.write(
            json.dumps(metadata, ensure_ascii=False) + "\n"
        )

    return log_path
