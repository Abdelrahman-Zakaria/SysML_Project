"""Provider layer. AnthropicProvider talks to the real API; FakeProvider is for tests and --provider fake."""
import json
import os
import socket
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Callable, Optional

API_URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2023-06-01"


class TeacherTimeout(Exception):
    pass


class ProviderError(Exception):
    def __init__(self, message, status: Optional[int] = None):
        super().__init__(message)
        self.status = status


@dataclass
class ProviderResponse:
    text: str
    usage: Optional[dict]          # {"input_tokens": int, "output_tokens": int} or None if not provided
    model_id: Optional[str] = None  # model the provider says it used


class AnthropicProvider:
    name = "anthropic"

    def __init__(self, model_id: str, timeout_s: float, max_tokens: int):
        key = os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise ProviderError("ANTHROPIC_API_KEY is not set. Export it in your shell; never put it in source.")
        self._key = key
        self.model_id = model_id
        self.timeout_s = timeout_s
        self.max_tokens = max_tokens

    def complete(self, system: str, user: str) -> ProviderResponse:
        body = json.dumps({
            "model": self.model_id,
            "max_tokens": self.max_tokens,
            "temperature": 0,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        }).encode("utf-8")
        req = urllib.request.Request(API_URL, data=body, method="POST", headers={
            "content-type": "application/json",
            "x-api-key": self._key,
            "anthropic-version": API_VERSION,
        })
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            raise ProviderError(f"HTTP {e.code} from provider", status=e.code) from e
        except (socket.timeout, TimeoutError) as e:
            raise TeacherTimeout(f"no response within {self.timeout_s}s") from e
        except urllib.error.URLError as e:
            if isinstance(e.reason, (socket.timeout, TimeoutError)):
                raise TeacherTimeout(f"no response within {self.timeout_s}s") from e
            raise ProviderError(f"network error: {e.reason}") from e
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            raise ProviderError("provider returned a non-JSON response envelope") from e

        blocks = payload.get("content") if isinstance(payload, dict) else None
        if not isinstance(blocks, list):
            raise ProviderError("provider response had no content blocks")
        text = "".join(b.get("text", "") for b in blocks if isinstance(b, dict) and b.get("type") == "text")
        raw_usage = payload.get("usage")
        usage = None
        if isinstance(raw_usage, dict) and all(isinstance(raw_usage.get(k), int)
                                               for k in ("input_tokens", "output_tokens")):
            usage = {"input_tokens": raw_usage["input_tokens"], "output_tokens": raw_usage["output_tokens"]}
        return ProviderResponse(text=text, usage=usage, model_id=payload.get("model"))


class FakeProvider:
    """Deterministic stand-in. `behavior` is a callable (system, user) -> ProviderResponse, or raises."""
    name = "fake"

    def __init__(self, behavior: Callable[[str, str], ProviderResponse], model_id: str = "fake-teacher-0"):
        self.behavior = behavior
        self.model_id = model_id

    def complete(self, system: str, user: str) -> ProviderResponse:
        return self.behavior(system, user)
