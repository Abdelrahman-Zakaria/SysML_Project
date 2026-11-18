import pytest
import httpx

from unittest.mock import Mock
from openai import APIConnectionError, APIStatusError

from src.inference import generate_response


def test_successful_inference(monkeypatch):

    mock_usage = Mock()
    mock_usage.prompt_tokens = 100
    mock_usage.completion_tokens = 50
    mock_usage.total_tokens = 150
    mock_usage.model_dump.return_value = {
        "prompt_tokens": 100,
        "completion_tokens": 50,
        "total_tokens": 150
    }

    mock_completion = Mock()
    mock_completion.choices = [Mock()]
    mock_completion.choices[0].message.content = '{"schema_version": "1.0"}'
    mock_completion.usage = mock_usage

    monkeypatch.setattr(
        "src.inference.client.chat.completions.create",
        Mock(return_value=mock_completion)
    )

    result = generate_response("Test project")

    assert result["response"] == '{"schema_version": "1.0"}'
    assert result["model_id"]
    assert result["duration_seconds"] >= 0
    assert result["usage"]["total_tokens"] == 150


def test_connection_error(monkeypatch):

    request = httpx.Request("POST", "https://example.com")

    mock_api = Mock(
        side_effect=APIConnectionError(request=request)
    )

    monkeypatch.setattr(
        "src.inference.client.chat.completions.create",
        mock_api
    )

    with pytest.raises(RuntimeError, match="Connection error"):
        generate_response("Test project")


def test_provider_error(monkeypatch):

    request = httpx.Request("POST", "https://example.com")

    response = httpx.Response(
        500,
        request=request,
        text="Internal Server Error"
    )

    mock_api = Mock(
        side_effect=APIStatusError(
            "Internal Server Error",
            response=response,
            body=None
        )
    )

    monkeypatch.setattr(
        "src.inference.client.chat.completions.create",
        mock_api
    )

    with pytest.raises(RuntimeError, match="Provider error 500"):
        generate_response("Test project")