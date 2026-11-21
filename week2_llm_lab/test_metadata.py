
import json
from types import SimpleNamespace

import pytest

from prompts import PROMPT_VERSION
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
    assert metadata["prompt_version"] == PROMPT_VERSION
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


def test_negative_inputs_are_rejected():
    with pytest.raises(ValueError):
        estimate_cost_usd(-1, 5)

    with pytest.raises(ValueError):
        build_run_metadata(SimpleNamespace(usage=None, model=None), -1.0)


def test_invalid_token_values_become_none():
    usage = SimpleNamespace(prompt_tokens=True, completion_tokens=-3, total_tokens="9")
    metadata = build_run_metadata(SimpleNamespace(usage=usage, model=None), 1.0)

    assert metadata["input_tokens"] is None
    assert metadata["output_tokens"] is None
    assert metadata["total_tokens"] is None


def test_provider_total_and_finish_reason_are_kept():
    usage = SimpleNamespace(prompt_tokens=10, completion_tokens=5, total_tokens=99)
    choice = SimpleNamespace(finish_reason="length")
    response = SimpleNamespace(usage=usage, model=None, choices=[choice])

    metadata = build_run_metadata(response, 1.0)

    assert metadata["total_tokens"] == 99
    assert metadata["finish_reason"] == "length"
