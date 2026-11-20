
from agent.tool_registry import TOOL_REGISTRY


def validate_tool_call(tool_name: str, arguments: dict) -> dict:
    """
    Validate tool name and arguments before execution.
    """

    # 1. Check tool existence
    if not isinstance(tool_name, str) or tool_name not in TOOL_REGISTRY:
        return {
            "valid": False,
            "error": "UNKNOWN_TOOL"
        }

    # 2. Check arguments type
    if not isinstance(arguments, dict):
        return {
            "valid": False,
            "error": "INVALID_ARGUMENT"
        }

    tool = TOOL_REGISTRY[tool_name]

    required = tool["required"]
    optional = tool["optional"]

    provided = set(arguments.keys())

    # 3. Check missing arguments
    if not required.issubset(provided):
        return {
            "valid": False,
            "error": "MISSING_ARGUMENT"
        }

    # 4. Check unexpected arguments
    if not provided.issubset(required | optional):
        return {
            "valid": False,
            "error": "UNEXPECTED_ARGUMENT"
        }

    # 5. Validate argument values
    for key, value in arguments.items():

        if not isinstance(value, str):
            return {
                "valid": False,
                "error": "INVALID_ARGUMENT",
                "message": f"{key} must be a string"
            }

        if not value.strip():
            return {
                "valid": False,
                "error": "INVALID_ARGUMENT",
                "message": f"{key} cannot be empty"
            }

    # 6. Tool-specific validation
    if tool_name == "list_available_items":
        if arguments["item_type"] not in {"Block", "Requirement"}:
            return {
                "valid": False,
                "error": "INVALID_ARGUMENT"
            }

    if tool_name == "check_condition":
        if arguments["condition"] not in {
            "exists",
            "has_attributes"
        }:
            return {
                "valid": False,
                "error": "UNSUPPORTED_CONDITION"
            }

    return {
        "valid": True
    }
