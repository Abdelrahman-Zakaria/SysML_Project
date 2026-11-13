
import pytest

from pydantic import ValidationError

from app import (
    ProjectIntent,
    IntentResponse,
    ProviderResult,
    ProviderError,
    validate_response,
    run_request
)


# 1. Valid JSON

def test_valid_json():

    valid_json = """
    {
        "schema_version": "1.0",
        "intent": {
            "action": "create",
            "project_type": "web_application",
            "description": "Library management system",
            "features": [
                "User login",
                "Book borrowing"
            ]
        }
    }
    """

    result = validate_response(valid_json)

    assert result.schema_version == "1.0"
    assert result.intent.action == "create"


# 2. Malformed JSON

def test_malformed_json():

    invalid_json = '{"schema_version": "1.0", "intent":'

    with pytest.raises(ValidationError):
        validate_response(invalid_json)


# 3. Missing required field

def test_missing_field():

    invalid_json = """
    {
        "schema_version": "1.0",
        "intent": {
            "action": "create",
            "project_type": "web_application",
            "description": "Library system"
        }
    }
    """

    with pytest.raises(ValidationError):
        validate_response(invalid_json)


# 4. Invalid enum value

def test_invalid_action():

    invalid_json = """
    {
        "schema_version": "1.0",
        "intent": {
            "action": "delete",
            "project_type": "web_application",
            "description": "Library system",
            "features": ["Login"]
        }
    }
    """

    with pytest.raises(ValidationError):
        validate_response(invalid_json)


# 5. Unknown field

def test_unknown_field():

    invalid_json = """
    {
        "schema_version": "1.0",
        "intent": {
            "action": "create",
            "project_type": "web_application",
            "description": "Library system",
            "features": ["Login"],
            "extra_field": "not allowed"
        }
    }
    """

    with pytest.raises(ValidationError):
        validate_response(invalid_json)


# 6. Timeout handling

def test_timeout_handling():

    def timeout_provider(request, system_prompt):
        raise TimeoutError("Request timed out")

    response = run_request(
        "Test request",
        system_prompt="",
        provider_fn=timeout_provider
    )

    assert response["metadata"]["status"] == "failed"
    assert response["metadata"]["error_type"] == "timeout"


# 7. Provider error

def test_provider_error():

    def failing_provider(request, system_prompt):
        raise ProviderError("Provider unavailable")

    response = run_request(
        "Test request",
        system_prompt="",
        provider_fn=failing_provider
    )

    assert response["metadata"]["status"] == "failed"
    assert response["metadata"]["error_type"] == "provider_error"


# 8. Invalid provider output

def test_invalid_output():

    def invalid_provider(request, system_prompt):

        return ProviderResult(
            text='{"schema_version": "1.0", "intent": {}}',
            usage=None
        )

    response = run_request(
        "Test request",
        system_prompt="",
        provider_fn=invalid_provider
    )

    assert response["metadata"]["status"] == "rejected"
    assert response["metadata"]["error_type"] == "invalid_output"


# 9. Successful request metadata

def test_successful_request_metadata():

    response = run_request("Test request")

    metadata = response["metadata"]

    assert response["result"] is not None
    assert metadata["status"] == "success"
    assert metadata["model_id"]
    assert metadata["prompt_version"]
    assert metadata["duration_seconds"] >= 0

    assert metadata["token_usage"]["input_tokens"] == 35
    assert metadata["token_usage"]["output_tokens"] == 45

    assert metadata["estimated_cost"] is None
