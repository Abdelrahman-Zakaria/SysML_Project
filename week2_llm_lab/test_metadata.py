
import json
from types import SimpleNamespace

import pytest

from metadata import (
    build_run_metadata,
    estimate_cost_usd,
    save_run_metadata,
)


def test_estimated_cost_is_correct():
    cost = estimate_cost_usd(672, 207)

    assert cost == pytest.approx(0.0001125)


def test_missing_usage_returns_none():
    response = SimpleNamespace(usage=None, model=None)

    metadata = build_run_metadata(response, 1.5)

    assert metadata["input_tokens"] is None
    assert metadata["output_tokens"] is None
    assert metadata["estimated_cost_usd"] is None


def test_total_tokens_are_calculated_if_missing():
    usage = SimpleNamespace(
        prompt_tokens=10,
        completion_tokens=5,
        total_tokens=None,
    )

    response = SimpleNamespace(usage=usage, model=None)

    metadata = build_run_metadata(response, 1.0)

    assert metadata["total_tokens"] == 15


def test_metadata_contains_required_information():
    usage = SimpleNamespace(
        prompt_tokens=100,
        completion_tokens=50,
        total_tokens=150,
    )

    response = SimpleNamespace(
        usage=usage,
        model="openai/gpt-oss-20b",
    )

    metadata = build_run_metadata(response, 2.5)

    assert metadata["provider"] == "groq"
    assert metadata["model_id"] == "openai/gpt-oss-20b"
    assert metadata["prompt_version"] == "intent-v1.0"
    assert metadata["duration_seconds"] == 2.5


def test_metadata_is_saved_as_jsonl(tmp_path):
    log_file = tmp_path / "logs" / "usage.jsonl"

    sample_metadata = {
        "model_id": "openai/gpt-oss-20b",
        "total_tokens": 150,
    }

    saved_path = save_run_metadata(
        sample_metadata,
        log_path=log_file
    )

    assert saved_path.exists()

    saved_data = json.loads(
        saved_path.read_text(encoding="utf-8").strip()
    )

    assert saved_data == sample_metadata
