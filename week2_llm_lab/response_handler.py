
"""
Parse and validate the raw response returned by the LLM.
"""

import json

from pydantic import ValidationError

from models import Intent


def parse_and_validate(raw_response: str) -> Intent:
    """
    Convert raw JSON text into a validated Intent object.
    """

    # Step 1: Parse the JSON text.
    try:
        data = json.loads(raw_response)

    except json.JSONDecodeError as exc:
        raise ValueError(
            "The LLM returned invalid JSON."
        ) from exc

    # Step 2: Validate the parsed data.
    try:
        return Intent.model_validate(data)

    except ValidationError as exc:
        raise ValueError(
            "The LLM response does not match the Intent schema."
        ) from exc
