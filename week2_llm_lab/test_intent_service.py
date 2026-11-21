
from types import SimpleNamespace

import pytest

from intent_service import generate_intent
from models import Intent


VALID_RESPONSE = """
{
    "schema_version": "1.0",
    "intent_type": "draft_requirement",
    "requirement_type": "functional",
    "requirement_text": "The elevator shall stop at the selected floor.",
    "clarification_needed": false,
    "clarification_question": null
}
"""


def make_fake_response(content):
    """Create a simulated LLM response."""

    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=content)
            )
        ]
    )


@pytest.fixture(autouse=True)
def disable_metadata_file_writes(monkeypatch):
    """
    Prevent unit tests from writing actual usage logs.
    """

    monkeypatch.setattr(
        "intent_service.save_run_metadata",
        lambda metadata: None
    )


# Test 1: A valid response should produce a validated Intent.
def test_generate_intent_returns_validated_object(monkeypatch):

    fake_response = make_fake_response(VALID_RESPONSE)

    def fake_generate_response(messages):
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"

        return fake_response

    monkeypatch.setattr(
        "intent_service.generate_response",
        fake_generate_response
    )

    intent, response, metadata = generate_intent(
        "Draft a functional elevator requirement."
    )

    assert isinstance(intent, Intent)
    assert intent.intent_type == "draft_requirement"
    assert intent.requirement_type == "functional"
    assert response is fake_response

    assert metadata["validation_status"] == "passed"
    assert metadata["validation_error"] is None


# Test 2: Empty response choices should be rejected.
def test_empty_response_choices_are_rejected(monkeypatch):

    fake_response = SimpleNamespace(choices=[])

    monkeypatch.setattr(
        "intent_service.generate_response",
        lambda messages: fake_response
    )

    with pytest.raises(ValueError, match="no response choices"):
        generate_intent("Draft a requirement.")


# Test 3: Empty response content should be rejected.
def test_empty_response_content_is_rejected(monkeypatch):

    fake_response = make_fake_response("")

    monkeypatch.setattr(
        "intent_service.generate_response",
        lambda messages: fake_response
    )

    with pytest.raises(ValueError, match="empty content"):
        generate_intent("Draft a requirement.")


# Test 4: Malformed JSON should be rejected.
def test_malformed_json_is_rejected(monkeypatch):

    fake_response = make_fake_response("{invalid json}")

    monkeypatch.setattr(
        "intent_service.generate_response",
        lambda messages: fake_response
    )

    with pytest.raises(ValueError, match="invalid JSON"):
        generate_intent("Draft a requirement.")


# Test 5: Invalid Intent schema should be rejected.
def test_invalid_intent_schema_is_rejected(monkeypatch):

    invalid_response = VALID_RESPONSE.replace(
        '"draft_requirement"',
        '"delete_project"'
    )

    fake_response = make_fake_response(invalid_response)

    monkeypatch.setattr(
        "intent_service.generate_response",
        lambda messages: fake_response
    )

    with pytest.raises(ValueError, match="does not match"):
        generate_intent("Draft a requirement.")
