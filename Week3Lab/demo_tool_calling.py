"""Runnable demo: simulated model-generated tool calls -> dispatcher -> results.

No LLM and no network. Run:  python demo_tool_calling.py
"""

import json

from tool_calling import ToolDispatcher

SIMULATED_MODEL_CALLS = [
    ("List books (valid)", {"name": "list_available_items", "arguments": {"category": "books"}}),
    ("List page 2, 3 per page", {"name": "list_available_items", "arguments": {"limit": 3, "offset": 3}}),
    ("Get metadata (valid)", {"name": "get_metadata", "arguments": {"item_id": "book-002"}}),
    ("Check in_stock", {"name": "check_condition", "arguments": {"item_id": "book-003", "condition": "in_stock"}}),
    ("Check price_below 25", {"name": "check_condition", "arguments": {"item_id": "elec-003", "condition": "price_below", "threshold": 25}}),
    ("REJECT: unknown tool", {"name": "delete_everything", "arguments": {}}),
    ("REJECT: missing argument", {"name": "get_metadata", "arguments": {}}),
    ("REJECT: extra argument", {"name": "get_metadata", "arguments": {"item_id": "book-001", "debug": True}}),
    ("REJECT: wrong type", {"name": "list_available_items", "arguments": {"limit": "5"}}),
    ("REJECT: value out of range", {"name": "list_available_items", "arguments": {"limit": 500}}),
    ("REJECT: bad enum value", {"name": "check_condition", "arguments": {"item_id": "book-001", "condition": "__import__('os')"}}),
    ("REJECT: missing record", {"name": "get_metadata", "arguments": {"item_id": "book-999"}}),
    ("REJECT: threshold required", {"name": "check_condition", "arguments": {"item_id": "book-001", "condition": "price_below"}}),
]

SIMULATED_RAW_JSON = [
    ("Raw JSON (valid)", '{"name": "get_metadata", "arguments": {"item_id": "stat-001"}}'),
    ("REJECT: malformed JSON", '{"name": "get_metadata", "arguments": '),
]


def show(label, result):
    status = "OK  " if result.ok else "FAIL"
    print(f"[{status}] {label}")
    print("       " + json.dumps(result.to_dict(), sort_keys=True))


def main():
    dispatcher = ToolDispatcher()
    print("Registered tools:", ", ".join(dispatcher.registry.names()))
    print("=" * 70)
    for label, call in SIMULATED_MODEL_CALLS:
        show(label, dispatcher.dispatch(call))
    for label, raw in SIMULATED_RAW_JSON:
        show(label, dispatcher.dispatch_json(raw))


if __name__ == "__main__":
    main()
