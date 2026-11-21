"""llm_client with InferenceClient mocked: no network, no real key."""

from types import SimpleNamespace

import pytest

import llm_client
from config import MAX_OUTPUT_TOKENS


def test_missing_api_key_raises(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="GROQ_API_KEY"):
        llm_client.create_client()


def test_empty_messages_rejected():
    with pytest.raises(ValueError):
        llm_client.generate_response([])


def test_request_uses_configured_limits_and_schema(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    captured = {}

    class FakeClient:
        def __init__(self, **kwargs):
            captured["init"] = kwargs

        def chat_completion(self, **kwargs):
            captured["call"] = kwargs
            return "RESPONSE"

    monkeypatch.setattr(llm_client, "InferenceClient", FakeClient)

    result = llm_client.generate_response([{"role": "user", "content": "hi"}])

    assert result == "RESPONSE"
    assert captured["init"]["model"] == "openai/gpt-oss-20b"
    assert captured["init"]["provider"] == "groq"
    assert captured["call"]["max_tokens"] == MAX_OUTPUT_TOKENS >= 1000
    assert captured["call"]["response_format"]["json_schema"]["strict"] is True


def test_temporary_failure_is_retried(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setattr("reliability.sleep", lambda d: None)
    from huggingface_hub import InferenceTimeoutError

    calls = []

    class FakeClient:
        def __init__(self, **kwargs):
            pass

        def chat_completion(self, **kwargs):
            calls.append(1)
            if len(calls) < 3:
                raise InferenceTimeoutError("slow")
            return SimpleNamespace(ok=True)

    monkeypatch.setattr(llm_client, "InferenceClient", FakeClient)

    assert llm_client.generate_response([{"role": "user", "content": "hi"}]).ok
    assert len(calls) == 3
