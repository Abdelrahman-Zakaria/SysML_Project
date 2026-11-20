
import json
from pathlib import Path


MODEL_PATH = Path(__file__).resolve().parents[1] / "data" / "model.json"


def load_model():
    """Load the local SysML model."""
    with MODEL_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def list_available_items(item_type: str) -> dict:
    """
    Return all model elements of a given type.
    Supported types: Block, Requirement
    """

    if not isinstance(item_type, str):
        return {
            "success": False,
            "error": "INVALID_ARGUMENT",
            "message": "item_type must be a string"
        }

    if item_type not in {"Block", "Requirement"}:
        return {
            "success": False,
            "error": "INVALID_ARGUMENT",
            "message": "Unsupported item type"
        }

    try:
        model = load_model()

        items = [
            {
                "id": element["id"],
                "name": element["name"],
                "type": element["type"]
            }
            for element in model["elements"]
            if element["type"] == item_type
        ]

        return {
            "success": True,
            "items": items,
            "count": len(items),
            "evidence": "Results retrieved from model.json"
        }

    except Exception:
        return {
            "success": False,
            "error": "TOOL_EXECUTION_FAILED"
        }
