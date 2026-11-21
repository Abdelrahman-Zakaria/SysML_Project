"""Retry behaviour: transport errors, status codes, Retry-After handling."""

from unittest.mock import Mock

import httpx2
import pytest
from huggingface_hub import InferenceTimeoutError
from huggingface_hub.utils import HfHubHTTPError

from config import MAX_RETRY_DELAY_SECONDS
from reliability import (
    calculate_retry_delay,
    call_with_retry,
    is_retryable_error,
)


def http_error(status, headers=None):
    response = Mock()
    response.status_code = status
    response.headers = {} if headers is None else headers
    return HfHubHTTPError(f"HTTP {status}", response=response)


@pytest.mark.parametrize("status", [429, 498, 500, 502, 503, 504])
def test_temporary_statuses_are_retryable(status):
    assert is_retryable_error(http_error(status))


@pytest.mark.parametrize("status", [400, 401, 403, 404, 422])
def test_client_errors_are_not_retryable(status):
    assert not is_retryable_error(http_error(status))


def test_error_classes_come_from_installed_libraries():
    assert is_retryable_error(InferenceTimeoutError("t"))
    assert is_retryable_error(httpx2.ConnectError("refused"))
    assert is_retryable_error(httpx2.RemoteProtocolError("dropped"))
    assert not is_retryable_error(ValueError("nope"))


def test_transport_error_is_retried_then_succeeds():
    attempts = []

    def operation():
        attempts.append(1)
        if len(attempts) == 1:
            raise httpx2.ConnectError("refused")
        return "ok"

    assert call_with_retry(operation, sleep_fn=lambda d: None) == "ok"
    assert len(attempts) == 2


def test_non_retryable_error_is_raised_immediately():
    calls = []

    def operation():
        calls.append(1)
        raise ValueError("bug")

    with pytest.raises(ValueError):
        call_with_retry(operation, sleep_fn=lambda d: None)
    assert len(calls) == 1


def test_retry_after_is_capped_at_30_seconds():
    delay = calculate_retry_delay(http_error(429, {"retry-after": "3600"}), 1)
    assert delay == MAX_RETRY_DELAY_SECONDS == 30.0


@pytest.mark.parametrize("value", ["abc", "", "nan", "inf", "-5",
                                   "Wed, 21 Oct 2026 07:28:00 GMT"])
def test_invalid_retry_after_falls_back_to_backoff(value):
    delay = calculate_retry_delay(http_error(429, {"retry-after": value}), 2)
    assert 2 <= delay <= 2.25


def test_missing_retry_after_header_falls_back_to_backoff():
    assert 1 <= calculate_retry_delay(http_error(503), 1) <= 1.25


def test_response_without_headers_is_safe():
    error = http_error(503)
    error.response.headers = None
    assert 1 <= calculate_retry_delay(error, 1) <= 1.25


def test_invalid_max_attempts():
    with pytest.raises(ValueError):
        call_with_retry(lambda: 1, max_attempts=0)
