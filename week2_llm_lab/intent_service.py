"""
Main service connecting prompting, inference,
response validation, and usage metadata.
"""

import logging
from time import perf_counter

from models import Intent
from prompts import build_messages
from llm_client import generate_response
from response_handler import parse_and_validate

from metadata import (
    build_run_metadata,
    save_run_metadata,
)

logger = logging.getLogger(__name__)


class LLMRequestError(RuntimeError):
    """The request to the LLM provider failed (after any retries)."""


def _record(metadata: dict) -> None:
    """Save metadata; a logging failure must never break the chatbot."""

    try:
        save_run_metadata(metadata)
    except OSError as exc:
        logger.warning("Could not write usage log: %s", exc)


def generate_intent(
    user_request: str,
    history: list[dict[str, str]] | None = None,
) -> tuple[Intent, object, dict]:
    """
    Generate, validate, and record one intent request.

    history optionally contains earlier chat messages for context.
    Raises ValueError for unusable model output and LLMRequestError
    for API failures. Every outcome is recorded in the usage log.
    """

    # 1. Prepare chat messages.
    messages = build_messages(user_request, history)

    # 2. Measure inference duration; record API failures too.
    start_time = perf_counter()
    try:
        response = generate_response(messages)
    except Exception as exc:
        failure = build_run_metadata(None, perf_counter() - start_time)
        failure["validation_status"] = "api_error"
        failure["validation_error"] = f"{type(exc).__name__}: {exc}"
        _record(failure)
        raise LLMRequestError(
            f"The LLM request failed ({type(exc).__name__}): {exc}"
        ) from exc
    duration = perf_counter() - start_time

    # 3. Collect usage and model metadata.
    metadata = build_run_metadata(response, duration)

    try:
        # 4. Check response choices.
        if not response.choices:
            raise ValueError(
                "The LLM returned no response choices."
            )

        choice = response.choices[0]

        # 5. A truncated reply is incomplete JSON; say so clearly.
        if getattr(choice, "finish_reason", None) == "length":
            raise ValueError(
                "The LLM response was truncated (finish_reason=length). "
                "Increase MAX_OUTPUT_TOKENS."
            )

        # 6. Extract generated text.
        raw_content = choice.message.content

        if not isinstance(raw_content, str) or not raw_content.strip():
            raise ValueError(
                "The LLM returned empty content."
            )

        # 7. Parse and validate JSON.
        intent = parse_and_validate(raw_content)

    except ValueError as exc:

        metadata["validation_status"] = "failed"
        metadata["validation_error"] = str(exc)

        _record(metadata)
        raise

    # 8. Record successful validation.
    metadata["validation_status"] = "passed"
    metadata["validation_error"] = None

    _record(metadata)

    return intent, response, metadata
