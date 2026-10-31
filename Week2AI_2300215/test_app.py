import pytest
from pydantic import ValidationError
from app import SystemModelingIntent, clean_json_payload

def test_valid_json_accepted():
    """Test that a perfectly formatted JSON string is accepted."""
    valid_json = '{"action": "generate", "target_component": "battery", "confidence_score": 0.95}'
    intent = SystemModelingIntent.model_validate_json(valid_json)
    assert intent.action == "generate"
    assert intent.target_component == "battery"
    assert intent.confidence_score == 0.95

def test_invalid_action_rejected():
    """Test that an action not in the Literal list throws an error."""
    # 'destroy' is not generate, validate, or extract
    bad_json = '{"action": "destroy", "target_component": "battery", "confidence_score": 0.95}'
    with pytest.raises(ValidationError):
        SystemModelingIntent.model_validate_json(bad_json)

def test_out_of_bounds_confidence_rejected():
    """Test that a confidence score over 1.0 throws an error."""
    # confidence_score = 1.5 violates le=1.0
    bad_json = '{"action": "extract", "target_component": "battery", "confidence_score": 1.5}'
    with pytest.raises(ValidationError):
        SystemModelingIntent.model_validate_json(bad_json)

def test_missing_required_field_rejected():
    """Test that missing the target_component field throws an error."""
    bad_json = '{"action": "validate", "confidence_score": 0.95}'
    with pytest.raises(ValidationError):
        SystemModelingIntent.model_validate_json(bad_json)

def test_json_cleaner():
    """Test that the cleaning function strips markdown blocks."""
    dirty_json = '```json\n{"action": "generate", "target_component": "battery", "confidence_score": 0.95}\n```'
    cleaned = clean_json_payload(dirty_json)
    assert cleaned == '{"action": "generate", "target_component": "battery", "confidence_score": 0.95}'