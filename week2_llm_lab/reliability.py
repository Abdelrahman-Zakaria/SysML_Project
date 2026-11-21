
"""
Retry utilities for temporary inference failures.
"""

from random import uniform
from time import sleep
from typing import Callable, TypeVar

from huggingface_hub import InferenceTimeoutError
from huggingface_hub.utils import HfHubHTTPError


T = TypeVar("T")

RETRYABLE_STATUS_CODES = {
    429,  # Rate limit
    498,  # Temporary capacity issue
    500,  # Internal server error
    502,  # Bad gateway
    503,  # Service unavailable
}


def is_retryable_error(error: Exception) -> bool:
    """Check whether the error may be temporary."""

    if isinstance(error, InferenceTimeoutError):
        return True

    if isinstance(error, HfHubHTTPError):
        response = error.response
        status_code = response.status_code

        return status_code in RETRYABLE_STATUS_CODES

    return False


def calculate_retry_delay(
    error: Exception,
    attempt: int,
) -> float:
    """Calculate the delay before the next attempt."""

    # Respect Retry-After when provided by the provider.
    if isinstance(error, HfHubHTTPError):
        retry_after = error.response.headers.get("retry-after")

        if retry_after is not None:
            try:
                return max(0.0, float(retry_after))
            except (TypeError, ValueError):
                pass

    # Exponential backoff with a small random jitter.
    backoff = min(2 ** (attempt - 1), 8)

    return backoff + uniform(0, 0.25)


def call_with_retry(
    operation: Callable[[], T],
    max_attempts: int = 3,
    sleep_fn: Callable[[float], None] = sleep,
) -> T:
    """
    Execute an operation with limited retries
    for temporary inference failures.
    """

    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1.")

    for attempt in range(1, max_attempts + 1):
        try:
            return operation()

        except (InferenceTimeoutError, HfHubHTTPError) as error:

            if not is_retryable_error(error):
                raise

            if attempt == max_attempts:
                raise

            delay = calculate_retry_delay(error, attempt)

            sleep_fn(delay)

    raise RuntimeError("Retry operation unexpectedly ended.")
