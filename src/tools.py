ELEVATOR_ITEMS = {
    1: {
        "name": "Elevator",
        "type": "Part",
        "status": "Available"
    },
    2: {
        "name": "Motor",
        "type": "Part",
        "status": "Available"
    },
    3: {
        "name": "Door",
        "type": "Part",
        "status": "Available"
    },
    4: {
        "name": "OverloadProtection",
        "type": "Requirement",
        "status": "Defined"
    },
    5: {
        "name": "LoadLimit",
        "type": "Constraint",
        "status": "Defined"
    }
}


def list_available_items():
    return ELEVATOR_ITEMS


def get_metadata(item_id: int):
    if item_id not in ELEVATOR_ITEMS:
        return {"error": f"Item {item_id} does not exist"}

    return ELEVATOR_ITEMS[item_id]


def check_condition(item_id: int, condition: str):
    if item_id not in ELEVATOR_ITEMS:
        return {"error": f"Item {item_id} does not exist"}

    item = ELEVATOR_ITEMS[item_id]

    if condition == "exists":
        return True

    if condition == "available":
        return item["status"] == "Available"

    if condition == "defined":
        return item["status"] == "Defined"

    return {"error": f"Unsupported condition: {condition}"}