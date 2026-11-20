"""Real LLM client backed by NVIDIA's OpenAI-compatible API."""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from typing import Optional


def _extract_json_dict(raw_text: str) -> dict:
    """Strip <think> tags or markdown fences and parse the model's action JSON."""
    text = re.sub(r"<think>.*?</think>", "", raw_text, flags=re.DOTALL).strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if len(lines) >= 3:
            text = "\n".join(lines[1:-1]).strip()

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        text = text[start : end + 1]

    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise ValueError(f"Expected JSON object from LLM, got {type(parsed).__name__}")
    return parsed


class NvidiaLLM:
    """Connects run_agent() to NVIDIA NIM and keeps the exact raw API responses."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
        temperature: float = 0.2,
    ) -> None:
        key = api_key or os.environ.get("NVIDIA_API_KEY", "").strip()
        if not key:
            raise RuntimeError("NVIDIA_API_KEY is not set in your environment.")
        self.api_key = key
        self.model = model
        self.temperature = temperature
        self.raw_api_responses: list[dict] = []  # Exact JSON returned by NVIDIA per turn

    def next_step(self, messages: list) -> dict:
        api_messages = []
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            payload = json.dumps(content) if isinstance(content, dict) else str(content)
            if role == "tool":
                api_messages.append({"role": "user", "content": f"TOOL_OBSERVATION:\n{payload}"})
            else:
                api_messages.append({"role": role, "content": payload})

        body = json.dumps({
            "model": self.model,
            "messages": api_messages,
            "temperature": self.temperature,
            "top_p": 0.95,
            "max_tokens": 4096,
            "reasoning_budget": 1024,
            "stream": False,
        }).encode("utf-8")

        url = url = "/".join(["https:", "", "integrate.api.nvidia.com", "v1", "chat", "completions"])
        req = urllib.request.Request(
            url,
            data=body,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                raw_api_json = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            err_body = exc.read().decode("utf-8", errors="replace")[:300]
            raise RuntimeError(f"NVIDIA HTTP {exc.code}: {err_body}") from exc

        # Save the exact, unmodified response from NVIDIA
        self.raw_api_responses.append(raw_api_json)

        raw_content = raw_api_json["choices"][0]["message"].get("content") or ""
        try:
            return _extract_json_dict(raw_content)
        except Exception as exc:
            raise RuntimeError(f"Model returned non-JSON output: {raw_content[:200]!r}") from exc