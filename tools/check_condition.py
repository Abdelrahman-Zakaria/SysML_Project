
from tools.list_items import load_model


SUPPORTED_CONDITIONS = {
    "exists",
    "has_attributes"
}


def check_condition(
    element_id: str,
    condition: str
) -> dict:
    """
    Check a deterministic condition on a model element.
    """

    if not isinstance(element_id, str):
        return {
            "success": False,
            "error": "INVALID_ARGUMENT"
        }

    if not isinstance(condition, str):
        return {
            "success": False,
            "error": "INVALID_ARGUMENT"
        }

    if not element_id.strip():
        return {
            "success": False,
            "error": "INVALID_ARGUMENT"
        }

    if condition not in SUPPORTED_CONDITIONS:
        return {
            "success": False,
            "error": "UNSUPPORTED_CONDITION"
        }

    try:
        model = load_model()

        element = next(
            (
                item for item in model["elements"]
                if item["id"] == element_id
            ),
            None
        )

        if element is None:
            return {
                "success": False,
                "error": "ELEMENT_NOT_FOUND"
            }

        if condition == "exists":
            result = True

        elif condition == "has_attributes":
            result = (
                element["type"] == "Block"
                and len(element.get("attributes", [])) > 0
            )

        return {
            "success": True,
            "result": result,
            "element_id": element_id,
            "condition": condition,
            "evidence": f"Condition checked against {element_id}"
        }

    except Exception:
        return {
            "success": False,
            "error": "TOOL_EXECUTION_FAILED"
        }
