
from tools.list_items import load_model


def get_metadata(element_id: str) -> dict:
    """
    Retrieve metadata for an existing model element.
    """

    if not isinstance(element_id, str):
        return {
            "success": False,
            "error": "INVALID_ARGUMENT",
            "message": "element_id must be a string"
        }

    if not element_id.strip():
        return {
            "success": False,
            "error": "INVALID_ARGUMENT",
            "message": "element_id cannot be empty"
        }

    try:
        model = load_model()

        for element in model["elements"]:
            if element["id"] == element_id:
                return {
                    "success": True,
                    "data": element,
                    "evidence": f"Element {element_id} found in model.json"
                }

        return {
            "success": False,
            "error": "ELEMENT_NOT_FOUND",
            "message": f"No element found with ID {element_id}"
        }

    except Exception:
        return {
            "success": False,
            "error": "TOOL_EXECUTION_FAILED"
        }
