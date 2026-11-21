import json

import pytest

from response_handler import parse_and_validate

VALID = {
    "schema_version": "1.0",
    "intent_type": "draft_requirement",
    "requirement_type": "functional",
    "requirement_text": "The system shall do X.",
    "clarification_needed": False,
    "clarification_question": None,
}


def test_valid_json_is_parsed():
    assert parse_and_validate(json.dumps(VALID)).requirement_type == "functional"


@pytest.mark.parametrize("raw", ["not json", "", '{"schema_version": "1.0"', "[1, 2]"])
def test_malformed_or_wrong_shape_is_rejected(raw):
    with pytest.raises(ValueError):
        parse_and_validate(raw)


def test_contradictory_fields_are_rejected():
    bad = {**VALID, "clarification_needed": True}
    with pytest.raises(ValueError, match="does not match"):
        parse_and_validate(json.dumps(bad))


def test_draft_without_text_or_question_is_rejected():
    bad = {**VALID, "requirement_text": None}
    with pytest.raises(ValueError, match="no requirement_text"):
        parse_and_validate(json.dumps(bad))
