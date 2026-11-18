
import pytest

from schemas import SystemIntent
from semantic_validation import (
    validate_semantics,
    SemanticValidationError
)


valid_data = {
    "schema_version": "1.0",
    "system_name": "Electric Vehicle Charging System",
    "system_type": "charging_system",
    "description": "A system for charging electric vehicles.",
    "components": [
        "Charging Unit",
        "Power Monitoring Unit"
    ],
    "requirements": [
        {
            "type": "performance",
            "description": "Support 10 vehicles simultaneously"
        },
        {
            "type": "functional",
            "description": "Include an emergency shutdown mechanism"
        }
    ],
    "constraints": []
}


def test_valid_components():
    intent = SystemIntent.model_validate(valid_data)

    validate_semantics(intent)


def test_duplicate_components():
    data = valid_data.copy()
    data["components"] = [
        "Battery",
        "Motor",
        "Battery"
    ]

    intent = SystemIntent.model_validate(data)

    with pytest.raises(SemanticValidationError):
        validate_semantics(intent)


def test_duplicate_components_with_different_case():
    data = valid_data.copy()
    data["components"] = [
        "Battery",
        "Motor",
        " battery "
    ]

    intent = SystemIntent.model_validate(data)

    with pytest.raises(SemanticValidationError):
        validate_semantics(intent)

def test_empty_component():
    data = valid_data.copy()
    data["components"] = [
        "Battery",
        "   "
    ]

    intent = SystemIntent.model_validate(data)

    with pytest.raises(SemanticValidationError):
        validate_semantics(intent)
