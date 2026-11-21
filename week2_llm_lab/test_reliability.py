
import pytest
from unittest.mock import Mock

from huggingface_hub import InferenceTimeoutError
from huggingface_hub.utils import HfHubHTTPError

from reliability import call_with_retry


def make_http_error(status_code, headers=None):
    response = Mock()
    response.status_code = status_code
    response.headers = headers or {}

    return HfHubHTTPError(
        f"HTTP {status_code}",
        response=response
    )


def test_success_does_not_retry():

    result = call_with_retry(
        lambda: "success",
        sleep_fn=lambda delay: None
    )

    assert result == "success"


def test_timeout_is_retried():

    attempts = 0
    delays = []

    def operation():
        nonlocal attempts
        attempts += 1

        if attempts == 1:
            raise InferenceTimeoutError("Request timed out")

        return "success"

    result = call_with_retry(
        operation,
        sleep_fn=delays.append
    )

    assert result == "success"
    assert attempts == 2
    assert len(delays) == 1


def test_rate_limit_respects_retry_after():

    attempts = 0
    delays = []

    error = make_http_error(
        429,
        {"retry-after": "0.5"}
    )

    def operation():
        nonlocal attempts
        attempts += 1

        if attempts == 1:
            raise error

        return "success"

    result = call_with_retry(
        operation,
        sleep_fn=delays.append
    )

    assert result == "success"
    assert delays == [0.5]


def test_authentication_error_is_not_retried():

    attempts = 0
    delays = []

    error = make_http_error(401)

    def operation():
        nonlocal attempts
        attempts += 1
        raise error

    with pytest.raises(HfHubHTTPError):
        call_with_retry(
            operation,
            sleep_fn=delays.append
        )

    assert attempts == 1
    assert delays == []


def test_retry_stops_after_max_attempts():

    attempts = 0
    delays = []

    error = make_http_error(503)

    def operation():
        nonlocal attempts
        attempts += 1
        raise error

    with pytest.raises(HfHubHTTPError):
        call_with_retry(
            operation,
            max_attempts=3,
            sleep_fn=delays.append
        )

# The jitter makes delays slightly random.
    assert len(delays) == 2
    assert 1 <= delays[0] <= 1.25
    assert 2 <= delays[1] <= 2.25
