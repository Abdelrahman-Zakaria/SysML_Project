"""Cross-field validation rules of the Intent model."""

import pytest
from pydantic import ValidationError

from models import Intent

BASE = {
    "schema_version": "1.0",
    "intent_type": "draft_requirement",
    "requirement_type": "functional",
    "requirement_text": "The system shall do X.",
    "clarification_needed": False,
    "clarification_question": None,
}


def build(**overrides):
    return Intent.model_validate({**BASE, **overrides})


def test_clarification_needed_requires_question():
    with pytest.raises(ValidationError):
        build(clarification_needed=True, clarification_question=None)


def test_question_without_clarification_is_rejected():
    with pytest.raises(ValidationError):
        build(clarification_needed=False, clarification_question="Why?")


def test_unsupported_cannot_have_requirement_text():
    with pytest.raises(ValidationError):
        build(intent_type="unsupported", requirement_text="text")


def test_unsupported_cannot_need_clarification():
    with pytest.raises(ValidationError):
        build(
            intent_type="unsupported",
            requirement_text=None,
            clarification_needed=True,
            clarification_question="Why?",
        )


@pytest.mark.parametrize("field", ["requirement_text", "clarification_question"])
def test_blank_text_is_rejected(field):
    with pytest.raises(ValidationError):
        build(**{field: "   ", "clarification_needed": field == "clarification_question"})


def test_valid_clarification_and_unsupported_are_accepted():
    build(
        requirement_type="unspecified",
        requirement_text=None,
        clarification_needed=True,
        clarification_question="What should it do?",
    )
    build(intent_type="unsupported", requirement_type="unspecified", requirement_text=None)
