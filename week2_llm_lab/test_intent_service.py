
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
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=content)
            )
        ]
    )


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

    intent, response = generate_intent(
        "Draft a functional elevator requirement."
    )

    assert isinstance(intent, Intent)
    assert intent.intent_type == "draft_requirement"
    assert response is fake_response


def test_empty_response_choices_are_rejected(monkeypatch):
    fake_response = SimpleNamespace(choices=[])

    monkeypatch.setattr(
        "intent_service.generate_response",
        lambda messages: fake_response
    )

    with pytest.raises(ValueError, match="no response choices"):
        generate_intent("Draft a requirement.")


def test_empty_response_content_is_rejected(monkeypatch):
    fake_response = make_fake_response("")

    monkeypatch.setattr(
        "intent_service.generate_response",
        lambda messages: fake_response
    )

    with pytest.raises(ValueError, match="empty content"):
        generate_intent("Draft a requirement.")


def test_malformed_json_is_rejected(monkeypatch):
    fake_response = make_fake_response("{invalid json}")

    monkeypatch.setattr(
        "intent_service.generate_response",
        lambda messages: fake_response
    )

    with pytest.raises(ValueError, match="invalid JSON"):
        generate_intent("Draft a requirement.")


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
