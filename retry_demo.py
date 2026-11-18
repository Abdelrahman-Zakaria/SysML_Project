
import httpx

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception
)

attempts = 0


def is_retryable_error(exc):
    return isinstance(exc, httpx.TimeoutException)


@retry(
    retry=retry_if_exception(is_retryable_error),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=4),
    reraise=True
)

def simulate_request():
    global attempts
    attempts += 1

    print(f"Attempt number: {attempts}")

    if attempts < 3:
        raise httpx.TimeoutException("Simulated timeout")

    return "Request succeeded!"

@retry(
    retry=retry_if_exception(is_retryable_error),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=4),
    reraise=True
)

def simulate_permanent_error():
    print("Attempt: Permanent Error")
    raise ValueError("Invalid input")

if __name__ == "__main__":
    try:
        simulate_permanent_error()
    except ValueError as e:
        print("Error:", e)