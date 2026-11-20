
from structured_output import build_response_format


def test_response_format_uses_json_schema():
    response_format = build_response_format()

    assert response_format["type"] == "json_schema"


def test_strict_mode_is_enabled():
    response_format = build_response_format()

    assert response_format["json_schema"]["strict"] is True


def test_all_intent_fields_are_required():
    schema = build_response_format()["json_schema"]["schema"]

    assert set(schema["required"]) == set(schema["properties"])


def test_extra_fields_are_forbidden():
    schema = build_response_format()["json_schema"]["schema"]

    assert schema["additionalProperties"] is False


def test_schema_version_has_allowed_value():
    schema = build_response_format()["json_schema"]["schema"]

    version_schema = schema["properties"]["schema_version"]

    assert version_schema["enum"] == ["1.0"]
    assert "const" not in version_schema
