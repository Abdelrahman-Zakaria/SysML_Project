import pytest

from src.validator import validate_response


VALID_RESPONSE = """
{
    "schema_version": "1.0",
    "project_name": "Smart Parking System",
    "project_type": "embedded",
    "main_components": ["Ultrasonic sensors"],
    "objectives": ["Detect available parking spaces"]
}
"""


def test_valid_response():

    result = validate_response(VALID_RESPONSE)

    assert result.project_name == "Smart Parking System"


def test_invalid_json():

    with pytest.raises(ValueError):
        validate_response("{invalid json}")


def test_missing_field():

    response = """
    {
        "schema_version": "1.0",
        "project_type": "embedded",
        "main_components": ["Sensors"],
        "objectives": ["Detect parking spaces"]
    }
    """

    with pytest.raises(ValueError):
        validate_response(response)


def test_invalid_enum():

    response = VALID_RESPONSE.replace("embedded", "gaming")

    with pytest.raises(ValueError):
        validate_response(response)


def test_wrong_data_type():

    response = VALID_RESPONSE.replace(
        '["Ultrasonic sensors"]',
        '"Ultrasonic sensors"'
    )

    with pytest.raises(ValueError):
        validate_response(response)


def test_unexpected_field():

    response = VALID_RESPONSE.replace(
        '"project_name": "Smart Parking System",',
        '"project_name": "Smart Parking System",'
        '"generated_code": "print(hello)",'
    )

    with pytest.raises(ValueError):
        validate_response(response)