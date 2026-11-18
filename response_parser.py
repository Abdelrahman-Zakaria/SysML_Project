
import json


class InvalidJSONResponse(ValueError):
    """Raised when the LLM response is not a valid JSON object."""


def parse_json_response(raw_response: str) -> dict:

    try:
        data = json.loads(raw_response)

    except (json.JSONDecodeError, TypeError) as e:
        raise InvalidJSONResponse(
            "The LLM response is not valid JSON."
        ) from e

    if not isinstance(data, dict):
        raise InvalidJSONResponse(
            "The LLM response must be a JSON object."
        )

    return data
