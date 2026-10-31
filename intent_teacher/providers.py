"""Teacher providers. The API key is read from the environment, never from source."""
import json
import os
import socket
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Optional

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"


class ConfigError(RuntimeError):
    """Missing key/model etc. Fix your environment, not the source."""


class TeacherTimeout(RuntimeError):
    pass


class ProviderError(RuntimeError):
    def __init__(self, message, status=None):
        super().__init__(message)
        self.status = status


@dataclass
class Completion:
    text: str
    model_id: str                 # model reported by the provider
    usage: Optional[dict] = None  # {"input_tokens": int, "output_tokens": int} if provided


class AnthropicProvider:
    name = "anthropic"

    def __init__(self, model, api_key=None, max_tokens=1024):
        self.model = model
        self.max_tokens = max_tokens
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self._api_key:
            raise ConfigError("ANTHROPIC_API_KEY is not set (export it in your shell; never edit source)")
        if not model:
            raise ConfigError("no model selected: pass --model or set TEACHER_MODEL")

    def complete(self, system, user, timeout):
        body = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        }
        req = urllib.request.Request(
            ANTHROPIC_URL,
            data=json.dumps(body).encode(),
            headers={
                "content-type": "application/json",
                "x-api-key": self._api_key,
                "anthropic-version": ANTHROPIC_VERSION,
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                payload = json.load(resp)
        except (socket.timeout, TimeoutError) as exc:
            raise TeacherTimeout(f"no response within {timeout}s") from exc
        except urllib.error.HTTPError as exc:
            detail = exc.read()[:300].decode("utf-8", "replace") if hasattr(exc, "read") else ""
            raise ProviderError(f"HTTP {exc.code}: {detail}", status=exc.code) from exc
        except urllib.error.URLError as exc:
            if isinstance(exc.reason, (socket.timeout, TimeoutError)):
                raise TeacherTimeout(f"no response within {timeout}s") from exc
            raise ProviderError(f"network error: {exc.reason}") from exc
        except json.JSONDecodeError as exc:
            raise ProviderError("provider returned a non-JSON HTTP body") from exc

        try:
            text = "".join(b.get("text", "") for b in payload["content"] if b.get("type") == "text")
        except (KeyError, TypeError, AttributeError) as exc:
            raise ProviderError("unexpected provider response shape") from exc
        usage = payload.get("usage") if isinstance(payload.get("usage"), dict) else None
        return Completion(text=text, model_id=payload.get("model", self.model), usage=usage)


_FAKE_INTENT = {
    "schema_version": "intent.v1",
    "project_type": "web_app",
    "goal": "Let a community library track which books are checked out.",
    "components": [
        {"name": "catalog", "purpose": "Store book titles and availability."},
        {"name": "checkout form", "purpose": "Record who borrowed a book and when."},
    ],
    "constraints": ["Runs on a single small server"],
    "risk_level": "low",
    "needs_clarification": False,
    "clarifying_questions": [],
}


class FakeProvider:
    """Offline stand-in so anyone can run the program with no secret and no network."""
    name = "fake"
    model = "fake-teacher-1"

    def __init__(self, mode="ok"):
        if mode not in {"ok", "malformed", "bad_json", "timeout", "provider_error"}:
            raise ConfigError(f"unknown fake mode: {mode}")
        self.mode = mode

    def complete(self, system, user, timeout):
        if self.mode == "timeout":
            raise TeacherTimeout(f"no response within {timeout}s (simulated)")
        if self.mode == "provider_error":
            raise ProviderError("HTTP 503: simulated outage", status=503)
        usage = {"input_tokens": 400, "output_tokens": 150}
        if self.mode == "bad_json":
            return Completion("Sure! Here is your intent: {oops", self.model, usage)
        if self.mode == "malformed":
            bad = dict(_FAKE_INTENT, risk_level="catastrophic", code="import os; os.system('x')")
            return Completion(json.dumps(bad), self.model, usage)
        return Completion(json.dumps(_FAKE_INTENT), self.model, usage)
