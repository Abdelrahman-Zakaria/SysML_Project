from pydantic import ValidationError
from src.schemas import ProjectIntent


def validate_response(response):

    try:
        intent = ProjectIntent.model_validate_json(response)
        return intent

    except ValidationError as e:
        raise ValueError(f"Invalid AI response: {e}") from e