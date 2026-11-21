"""generate_intent: truncation, API failures, logging, history, usage."""

from types import SimpleNamespace

import pytest

import intent_service
from intent_service import LLMRequestError, generate_intent
from test_intent_service import VALID_RESPONSE


def response(content=VALID_RESPONSE, finish_reason="stop", usage=None, model=None):
    return SimpleNamespace(
        choices=[SimpleNamespace(
            message=SimpleNamespace(content=content),
            finish_reason=finish_reason,
        )],
        usage=usage,
        model=model,
    )


@pytest.fixture
def saved(monkeypatch):
    """Capture metadata records instead of writing the real log."""
    records = []
    monkeypatch.setattr("intent_service.save_run_metadata", records.append)
    return records


def use(monkeypatch, fake):
    monkeypatch.setattr("intent_service.generate_response", fake)


def test_truncated_response_is_reported_and_logged(monkeypatch, saved):
    use(monkeypatch, lambda m: response('{"schema_version": "1', finish_reason="length"))

    with pytest.raises(ValueError, match="truncated"):
        generate_intent("Draft a requirement.")

    assert saved[0]["validation_status"] == "failed"
    assert saved[0]["finish_reason"] == "length"


def test_truncation_with_empty_content_reports_truncation(monkeypatch, saved):
    use(monkeypatch, lambda m: response("", finish_reason="length"))

    with pytest.raises(ValueError, match="truncated"):
        generate_intent("Draft a requirement.")


def test_api_failure_is_recorded_and_wrapped(monkeypatch, saved):
    def boom(messages):
        raise ConnectionError("network down")

    use(monkeypatch, boom)

    with pytest.raises(LLMRequestError, match="network down"):
        generate_intent("Draft a requirement.")

    assert saved[0]["validation_status"] == "api_error"
    assert "ConnectionError" in saved[0]["validation_error"]
    assert saved[0]["input_tokens"] is None


def test_missing_api_key_is_recorded(monkeypatch, saved):
    def no_key(messages):
        raise RuntimeError("Missing API key. Set GROQ_API_KEY in .env.")

    use(monkeypatch, no_key)

    with pytest.raises(LLMRequestError, match="Missing API key"):
        generate_intent("Draft a requirement.")
    assert saved[0]["validation_status"] == "api_error"


def test_validation_failure_is_recorded(monkeypatch, saved):
    use(monkeypatch, lambda m: response("{invalid json}"))

    with pytest.raises(ValueError, match="invalid JSON"):
        generate_intent("Draft a requirement.")

    assert len(saved) == 1
    assert saved[0]["validation_status"] == "failed"


def test_success_records_usage_from_provider(monkeypatch, saved):
    usage = SimpleNamespace(prompt_tokens=672, completion_tokens=232, total_tokens=904)
    use(monkeypatch, lambda m: response(usage=usage, model="openai/gpt-oss-20b"))

    _intent, _resp, metadata = generate_intent("Draft a requirement.")

    assert saved == [metadata]
    assert metadata["validation_status"] == "passed"
    assert metadata["input_tokens"] == 672
    assert metadata["total_tokens"] == 904
    assert metadata["estimated_cost_usd"] == pytest.approx(0.00012)
    assert metadata["finish_reason"] == "stop"


def test_history_is_sent_between_system_and_new_message(monkeypatch, saved):
    seen = {}

    def fake(messages):
        seen["messages"] = messages
        return response()

    use(monkeypatch, fake)
    history = [
        {"role": "user", "content": "earlier"},
        {"role": "assistant", "content": "{}"},
    ]

    generate_intent("  new request ", history)

    roles = [m["role"] for m in seen["messages"]]
    assert roles == ["system", "user", "assistant", "user"]
    assert seen["messages"][-1]["content"] == "new request"


def test_log_write_failure_does_not_crash(monkeypatch):
    def broken_save(metadata):
        raise OSError("disk full")

    monkeypatch.setattr("intent_service.save_run_metadata", broken_save)
    use(monkeypatch, lambda m: response())

    intent, _resp, _meta = generate_intent("Draft a requirement.")
    assert intent.intent_type == "draft_requirement"
