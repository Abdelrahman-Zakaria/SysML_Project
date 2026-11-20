import json
from pydantic import ValidationError

from src.tools import (
    list_available_items,
    get_metadata,
    check_condition
)

from src.schemas import (
    ListAvailableItemsInput,
    ItemIdInput,
    CheckConditionInput
)


TOOL_REGISTRY = {
    "list_available_items": {
        "function": list_available_items,
        "schema": ListAvailableItemsInput
    },

    "get_metadata": {
        "function": get_metadata,
        "schema": ItemIdInput
    },

    "check_condition": {
        "function": check_condition,
        "schema": CheckConditionInput
    }
}


def execute_tool(tool_name: str, arguments: dict):

    if tool_name not in TOOL_REGISTRY:
        return {"error": f"Unknown tool: {tool_name}"}

    tool = TOOL_REGISTRY[tool_name]

    try:
        validated_args = tool["schema"].model_validate(arguments)

    except ValidationError as error:
        return {
            "error": "Invalid arguments",
            "details": error.errors()
        }

    try:
        result = tool["function"](**validated_args.model_dump())
        return {"result": result}

    except Exception as error:
        return {"error": f"Tool execution failed: {str(error)}"}