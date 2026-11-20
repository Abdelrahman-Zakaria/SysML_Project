
from tools.list_items import load_model


SUPPORTED_TYPES = {
    "Real",
    "Integer",
    "Boolean",
    "String"
}


def validate_operation(operation: dict) -> dict:
    """
    Perform local checks on a proposed SysML operation.
    This is NOT an official SysML compiler.
    """

    if not isinstance(operation, dict):
        return {
            "success": False,
            "error": "INVALID_OPERATION"
        }

    required = {
        "operation",
        "owner",
        "name",
        "type"
    }

    if set(operation.keys()) != required:
        return {
            "success": False,
            "error": "INVALID_OPERATION_SCHEMA"
        }

    if operation["operation"] != "add_attribute":
        return {
            "success": False,
            "error": "UNSUPPORTED_OPERATION"
        }

    for key in ("owner", "name", "type"):
        value = operation[key]

        if not isinstance(value, str) or not value.strip():
            return {
                "success": False,
                "error": "INVALID_OPERATION"
            }

    if not operation["name"].isidentifier():
        return {
            "success": False,
            "error": "INVALID_ATTRIBUTE_NAME"
        }

    if operation["type"] not in SUPPORTED_TYPES:
        return {
            "success": False,
            "error": "UNSUPPORTED_TYPE"
        }

    try:
        model = load_model()

        owner = next(
            (
                element for element in model["elements"]
                if element["name"] == operation["owner"]
                and element["type"] == "Block"
            ),
            None
        )

        if owner is None:
            return {
                "success": False,
                "error": "OWNER_NOT_FOUND"
            }

        existing_attributes = owner.get("attributes", [])

        if any(
            attribute["name"] == operation["name"]
            for attribute in existing_attributes
        ):
            return {
                "success": False,
                "error": "ATTRIBUTE_ALREADY_EXISTS"
            }

        return {
            "success": True,
            "local_validated": True,
            "candidate": operation,
            "evidence": (
                f"Block {owner['name']} exists, "
                f"and attribute {operation['name']} is not duplicated."
            )
        }

    except Exception:
        return {
            "success": False,
            "error": "TOOL_EXECUTION_FAILED"
        }
