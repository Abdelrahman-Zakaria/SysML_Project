
"""
Main service connecting prompting, inference,
response validation, and usage metadata.
"""

from time import perf_counter

from models import Intent
from prompts import build_messages
from llm_client import generate_response
from response_handler import parse_and_validate

from metadata import (
    build_run_metadata,
    save_run_metadata,
)


def generate_intent(user_request: str) -> tuple[Intent, object, dict]:
    """
    Generate, validate, and record one intent request.
    """

    # 1. Prepare chat messages.
    messages = build_messages(user_request)

    # 2. Measure inference duration.
    start_time = perf_counter()
    response = generate_response(messages)
    duration = perf_counter() - start_time

    # 3. Collect usage and model metadata.
    metadata = build_run_metadata(response, duration)

    try:
        # 4. Check response choices.
        if not response.choices:
            raise ValueError(
                "The LLM returned no response choices."
            )

        # 5. Extract generated text.
        raw_content = response.choices[0].message.content

        if not isinstance(raw_content, str) or not raw_content.strip():
            raise ValueError(
                "The LLM returned empty content."
            )

        # 6. Parse and validate JSON.
        intent = parse_and_validate(raw_content)

    except ValueError as exc:

        metadata["validation_status"] = "failed"
        metadata["validation_error"] = str(exc)

        save_run_metadata(metadata)
        raise

    # 7. Record successful validation.
    metadata["validation_status"] = "passed"
    metadata["validation_error"] = None

    save_run_metadata(metadata)

    return intent, response, metadata
