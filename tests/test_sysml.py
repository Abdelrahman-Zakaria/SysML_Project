
from validation.operation_validator import validate_operation
from validation.compiler_validator import validate_with_compiler


def valid_operation():

    return {
        "operation": "add_attribute",
        "owner": "System",
        "name": "temperature",
        "type": "Real"
    }


def test_valid_operation():

    result = validate_operation(valid_operation())

    assert result["success"] is True
    assert result["local_validated"] is True


def test_unknown_owner():

    operation = valid_operation()
    operation["owner"] = "UnknownBlock"

    result = validate_operation(operation)

    assert result["success"] is False
    assert result["error"] == "OWNER_NOT_FOUND"


def test_unsupported_type():

    operation = valid_operation()
    operation["type"] = "MagicType"

    result = validate_operation(operation)

    assert result["success"] is False
    assert result["error"] == "UNSUPPORTED_TYPE"


def test_duplicate_attribute():

    operation = valid_operation()
    operation["name"] = "voltage"

    result = validate_operation(operation)

    assert result["success"] is False
    assert result["error"] == "ATTRIBUTE_ALREADY_EXISTS"


def test_invalid_operation():

    operation = valid_operation()
    operation["operation"] = "delete_model"

    result = validate_operation(operation)

    assert result["success"] is False
    assert result["error"] == "UNSUPPORTED_OPERATION"


def test_compiler_not_configured(monkeypatch):

    monkeypatch.delenv("SYSML_VALIDATOR_CMD", raising=False)

    result = validate_with_compiler(
        "part def System {}"
    )

    assert result["success"] is False
    assert result["error"] == "COMPILER_NOT_CONFIGURED"
