
import pytest
from pydantic import ValidationError

from schemas import SystemIntent


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


def test_valid_data():
    intent = SystemIntent.model_validate(valid_data)

    assert intent.system_type == "charging_system"


def test_invalid_system_type():
    data = valid_data.copy()
    data["system_type"] = "battery"

    with pytest.raises(ValidationError):
        SystemIntent.model_validate(data)


def test_invalid_schema_version():
    data = valid_data.copy()
    data["schema_version"] = "2.0"

    with pytest.raises(ValidationError):
        SystemIntent.model_validate(data)


def test_empty_requirements():
    data = valid_data.copy()
    data["requirements"] = []

    with pytest.raises(ValidationError):
        SystemIntent.model_validate(data)
        
def test_invalid_requirement_type():
    data = valid_data.copy()
    data["requirements"] = [
        {
            "type": "constraint",
            "description": "Operate between -10 and 50 degrees"
        }
    ]

    with pytest.raises(ValidationError):
        SystemIntent.model_validate(data)
        
def test_missing_requirement_description():
    data = valid_data.copy()
    data["requirements"] = [
        {
            "type": "functional"
        }
    ]

    with pytest.raises(ValidationError):
        SystemIntent.model_validate(data)

def test_extra_field():
    data = valid_data.copy()
    data["unknown_field"] = "unexpected"

    with pytest.raises(ValidationError):
        SystemIntent.model_validate(data)
        

