"""
Retry utilities for temporary inference failures.

Exception classes (verified against huggingface_hub 2.x):
- InferenceTimeoutError: any timeout raised by InferenceClient.
- HfHubHTTPError: non-2xx HTTP responses (has .response).
- httpx2.TransportError: connection / protocol failures that
  InferenceClient does not wrap (ConnectError, RemoteProtocolError, ...).
"""

import math
from random import uniform
from time import sleep
from typing import Callable, TypeVar

import httpx2
from huggingface_hub import InferenceTimeoutError
from huggingface_hub.utils import HfHubHTTPError

from config import MAX_RETRY_ATTEMPTS, MAX_RETRY_DELAY_SECONDS


T = TypeVar("T")

RETRYABLE_STATUS_CODES = {
    429,  # Rate limit
    498,  # Temporary capacity issue
    500,  # Internal server error
    502,  # Bad gateway
    503,  # Service unavailable
    504,  # Gateway timeout
}


def is_retryable_error(error: Exception) -> bool:
    """Check whether the error may be temporary."""

    if isinstance(error, InferenceTimeoutError):
        return True

    if isinstance(error, HfHubHTTPError):
        status_code = getattr(error.response, "status_code", None)
        return status_code in RETRYABLE_STATUS_CODES

    # Connection reset, DNS failure, dropped connection, ...
    return isinstance(error, httpx2.TransportError)


def parse_retry_after(error: Exception) -> float | None:
    """Return a valid Retry-After value in seconds, or None."""

    if not isinstance(error, HfHubHTTPError):
        return None

    headers = getattr(error.response, "headers", None)
    if headers is None:
        return None

    try:
        retry_after = headers.get("retry-after")
        seconds = float(retry_after)
    except (AttributeError, TypeError, ValueError):
        # Missing header, or an HTTP-date we do not parse.
        return None

    if not math.isfinite(seconds) or seconds < 0:
        return None

    return seconds


def calculate_retry_delay(
    error: Exception,
    attempt: int,
) -> float:
    """Calculate the delay before the next attempt (never above the cap)."""

    # Respect Retry-After when provided, but never wait too long.
    retry_after = parse_retry_after(error)
    if retry_after is not None:
        return min(retry_after, MAX_RETRY_DELAY_SECONDS)

    # Exponential backoff with a small random jitter.
    backoff = min(2 ** (attempt - 1), 8)

    return min(backoff + uniform(0, 0.25), MAX_RETRY_DELAY_SECONDS)


def call_with_retry(
    operation: Callable[[], T],
    max_attempts: int = MAX_RETRY_ATTEMPTS,
    sleep_fn: Callable[[float], None] | None = None,
) -> T:
    """
    Execute an operation with limited retries
    for temporary inference failures.
    """

    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1.")

    # Resolved at call time so tests can patch reliability.sleep.
    sleep_fn = sleep_fn or sleep

    for attempt in range(1, max_attempts + 1):
        try:
            return operation()

        except Exception as error:

            if not is_retryable_error(error):
                raise

            if attempt == max_attempts:
                raise

            sleep_fn(calculate_retry_delay(error, attempt))

    raise RuntimeError("Retry operation unexpectedly ended.")
