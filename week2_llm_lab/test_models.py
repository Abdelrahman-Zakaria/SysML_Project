
import pytest
from pydantic import ValidationError

from models import Intent


# A valid example that follows our Intent contract.
VALID_INTENT = {
    "schema_version": "1.0",
    "intent_type": "draft_requirement",
    "requirement_type": "functional",
    "requirement_text": (
        "The elevator shall stop at the floor "
        "selected by the passenger."
    ),
    "clarification_needed": False,
    "clarification_question": None,
}


# Test 1: Valid data should be accepted.
def test_valid_intent_is_accepted():
    intent = Intent.model_validate(VALID_INTENT)

    assert intent.intent_type == "draft_requirement"
    assert intent.requirement_type == "functional"


# Test 2: Missing required fields should be rejected.
def test_missing_field_is_rejected():
    invalid_data = VALID_INTENT.copy()
    del invalid_data["requirement_text"]

    with pytest.raises(ValidationError):
        Intent.model_validate(invalid_data)


# Test 3: Invalid enum values should be rejected.
def test_invalid_intent_type_is_rejected():
    invalid_data = VALID_INTENT.copy()
    invalid_data["intent_type"] = "delete_project"

    with pytest.raises(ValidationError):
        Intent.model_validate(invalid_data)


# Test 4: Unknown extra fields should be rejected.
def test_extra_field_is_rejected():
    invalid_data = VALID_INTENT.copy()
    invalid_data["unexpected_action"] = "modify_model"

    with pytest.raises(ValidationError):
        Intent.model_validate(invalid_data)


# Test 5: Nullable fields should accept None.
def test_nullable_fields_accept_none():
    valid_data = VALID_INTENT.copy()

    valid_data["requirement_text"] = None
    valid_data["clarification_question"] = None

    intent = Intent.model_validate(valid_data)

    assert intent.requirement_text is None
    assert intent.clarification_question is None


# Test 6: Invalid schema versions should be rejected.
def test_invalid_schema_version_is_rejected():
    invalid_data = VALID_INTENT.copy()
    invalid_data["schema_version"] = "2.0"

    with pytest.raises(ValidationError):
        Intent.model_validate(invalid_data)
