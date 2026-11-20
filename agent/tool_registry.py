
from tools.list_items import list_available_items
from tools.get_metadata import get_metadata
from tools.check_condition import check_condition


TOOL_REGISTRY = {
    "list_available_items": {
        "function": list_available_items,
        "required": {"item_type"},
        "optional": set()
    },

    "get_metadata": {
        "function": get_metadata,
        "required": {"element_id"},
        "optional": set()
    },

    "check_condition": {
        "function": check_condition,
        "required": {"element_id", "condition"},
        "optional": set()
    }
}
