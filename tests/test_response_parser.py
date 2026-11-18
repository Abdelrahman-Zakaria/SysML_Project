
import pytest

from response_parser import (
    parse_json_response,
    InvalidJSONResponse
)


def test_valid_json_object():
    raw_response = '{"system_name": "Charging System"}'

    result = parse_json_response(raw_response)

    assert result["system_name"] == "Charging System"


def test_malformed_json():
    raw_response = '{"system_name": "Charging System"'

    with pytest.raises(InvalidJSONResponse):
        parse_json_response(raw_response)


def test_json_array_instead_of_object():
    raw_response = '["Battery", "Motor"]'

    with pytest.raises(InvalidJSONResponse):
        parse_json_response(raw_response)


def test_empty_response():
    raw_response = ""

    with pytest.raises(InvalidJSONResponse):
        parse_json_response(raw_response)
