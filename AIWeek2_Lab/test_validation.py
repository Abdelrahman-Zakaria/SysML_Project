from types import SimpleNamespace

import pytest
from pydantic import ValidationError

import app
from app import SystemModelingIntent, clean_json_payload


def test_clean_json_payload_extracts_json_from_markdown():
    raw_text = 'Here is the result:\n```json\n{"action":"extract","target_component":"Engine","confidence_score":0.8}\n```'
    assert clean_json_payload(raw_text) == (
        '{"action":"extract","target_component":"Engine","confidence_score":0.8}'
    )


def test_clean_json_payload_handles_nested_json():
    raw_text = 'Result: {"action":"generate","target_component":"Engine","confidence_score":0.7,"metadata":{"source":"model"}}'
    assert clean_json_payload(raw_text) == (
        '{"action":"generate","target_component":"Engine","confidence_score":0.7,"metadata":{"source":"model"}}'
    )


class FakeInferenceClient:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def chat_completion(self, **kwargs):
        self.calls.append(kwargs)
        return self.response


def configure_test_environment(monkeypatch):
    monkeypatch.setenv("BASE_URL", "https://example.test/v1")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("MODEL_ID", "test-model")


def test_get_model_intent_returns_validated_response(monkeypatch):
    configure_test_environment(monkeypatch)
    response = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content='{"action":"validate","target_component":"Engine","confidence_score":0.9}'
                )
            )
        ]
    )
    client = FakeInferenceClient(response)
    monkeypatch.setattr(app, "InferenceClient", lambda **kwargs: client)

    intent = app.get_model_intent("Check the engine")

    assert intent == SystemModelingIntent(
        action="validate",
        target_component="Engine",
        confidence_score=0.9,
    )
    assert client.calls[0]["model"] == "test-model"


def test_get_model_intent_returns_none_for_invalid_json(monkeypatch):
    configure_test_environment(monkeypatch)
    response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="not JSON"))]
    )
    monkeypatch.setattr(
        app,
        "InferenceClient",
        lambda **kwargs: FakeInferenceClient(response),
    )

    assert app.get_model_intent("Check the engine") is None


def test_get_model_intent_returns_none_when_configuration_is_missing(monkeypatch):
    monkeypatch.delenv("MODEL_ID", raising=False)

    assert app.get_model_intent("Check the engine") is None


def test_get_model_intent_returns_none_on_timeout(monkeypatch):
    configure_test_environment(monkeypatch)

    class TimeoutClient:
        def __init__(self, **kwargs):
            pass

        def chat_completion(self, **kwargs):
            raise TimeoutError

    monkeypatch.setattr(app, "InferenceClient", TimeoutClient)

    assert app.get_model_intent("Check the engine") is None


def test_valid_intent():
    data = {"action": "generate", "target_component": "Propulsion_Block", "confidence_score": 0.85}
    intent = SystemModelingIntent.model_validate(data)
    assert intent.action == "generate"
    assert intent.target_component == "Propulsion_Block"

def test_invalid_action_enum():
    data = {"action": "delete", "target_component": "Propulsion_Block", "confidence_score": 0.9}
    with pytest.raises(ValidationError):
        SystemModelingIntent.model_validate(data)

def test_out_of_bounds_confidence():
    data = {"action": "validate", "target_component": "Thermal_Subsystem", "confidence_score": 1.5}
    with pytest.raises(ValidationError):
        SystemModelingIntent.model_validate(data)

def test_missing_required_field():
    data = {"action": "extract", "confidence_score": 0.99}
    with pytest.raises(ValidationError):
        SystemModelingIntent.model_validate(data)