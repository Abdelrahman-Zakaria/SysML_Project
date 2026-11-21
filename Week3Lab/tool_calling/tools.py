"""The three deterministic local tools.

Each tool = ToolSpec (name, description, JSON Schema, handler).
Handlers receive ALREADY-VALIDATED keyword arguments and return a typed
dataclass. Domain failures are raised as ToolError (never returned as strings).
"""

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

from .catalog import CATEGORIES, CatalogItem, all_items, find_item
from .errors import INVALID_VALUE, MISSING_ARGUMENT, NOT_FOUND, ToolError

ITEM_ID_PATTERN = r"[a-z]{3,5}-[0-9]{3}"
MAX_LIST_LIMIT = 20
DEFAULT_LIST_LIMIT = 10
DEFAULT_LOW_STOCK_THRESHOLD = 5
CONDITIONS = ("in_stock", "on_sale", "low_stock", "price_below")


# ----------------------------------------------------------------- typed results
@dataclass(frozen=True)
class ItemSummary:
    item_id: str
    name: str
    category: str


@dataclass(frozen=True)
class ItemList:
    items: Tuple[ItemSummary, ...]
    total: int
    returned: int
    offset: int
    has_more: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "items": [
                {"item_id": i.item_id, "name": i.name, "category": i.category}
                for i in self.items
            ],
            "total": self.total,
            "returned": self.returned,
            "offset": self.offset,
            "has_more": self.has_more,
        }


@dataclass(frozen=True)
class ItemMetadata:
    item_id: str
    name: str
    category: str
    price: float
    stock: int
    on_sale: bool
    tags: Tuple[str, ...]
    updated: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "item_id": self.item_id,
            "name": self.name,
            "category": self.category,
            "price": self.price,
            "stock": self.stock,
            "on_sale": self.on_sale,
            "tags": list(self.tags),
            "updated": self.updated,
        }


@dataclass(frozen=True)
class ConditionOutcome:
    item_id: str
    condition: str
    satisfied: bool
    observed: Any  # the value that was compared (stock count, price, on_sale flag)
    threshold: Optional[float]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "item_id": self.item_id,
            "condition": self.condition,
            "satisfied": self.satisfied,
            "observed": self.observed,
            "threshold": self.threshold,
        }


# --------------------------------------------------------------------- handlers
def list_available_items(category: Optional[str] = None, limit: int = DEFAULT_LIST_LIMIT, offset: int = 0) -> ItemList:
    """Page through catalog items, optionally filtered by category."""
    pool: List[CatalogItem] = [
        i for i in all_items() if category is None or i.category == category
    ]
    page = pool[offset : offset + limit]  # bounded: limit <= MAX_LIST_LIMIT
    return ItemList(
        items=tuple(ItemSummary(i.item_id, i.name, i.category) for i in page),
        total=len(pool),
        returned=len(page),
        offset=offset,
        has_more=offset + len(page) < len(pool),
    )


def _require_item(item_id: str) -> CatalogItem:
    item = find_item(item_id)
    if item is None:
        raise ToolError(NOT_FOUND, f"No item with id '{item_id}'.")
    return item


def get_metadata(item_id: str) -> ItemMetadata:
    """Return the full metadata record for one item."""
    i = _require_item(item_id)
    return ItemMetadata(i.item_id, i.name, i.category, i.price, i.stock, i.on_sale, i.tags, i.updated)


def check_condition(item_id: str, condition: str, threshold: Optional[float] = None) -> ConditionOutcome:
    """Evaluate one named condition against one item (fixed set, no expressions)."""
    item = _require_item(item_id)

    if condition in ("in_stock", "on_sale") and threshold is not None:
        raise ToolError(INVALID_VALUE, f"Condition '{condition}' does not accept a threshold.")

    if condition == "in_stock":
        return ConditionOutcome(item.item_id, condition, item.stock > 0, item.stock, None)
    if condition == "on_sale":
        return ConditionOutcome(item.item_id, condition, item.on_sale, item.on_sale, None)
    if condition == "low_stock":
        limit = DEFAULT_LOW_STOCK_THRESHOLD if threshold is None else threshold
        return ConditionOutcome(item.item_id, condition, 0 < item.stock <= limit, item.stock, limit)
    if condition == "price_below":
        if threshold is None:
            raise ToolError(MISSING_ARGUMENT, "Condition 'price_below' requires a 'threshold'.")
        return ConditionOutcome(item.item_id, condition, item.price < threshold, item.price, threshold)
    # Unreachable after schema validation, but kept as a defensive guard.
    raise ToolError(INVALID_VALUE, f"Unsupported condition '{condition}'.")


# ------------------------------------------------------------------ tool specs
@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    input_schema: Dict[str, Any]
    handler: Callable[..., Any]


LIST_AVAILABLE_ITEMS = ToolSpec(
    name="list_available_items",
    description=(
        "List catalog items (id, name, category), optionally filtered by category. "
        "Paginated: use limit/offset. Use this first to discover valid item ids."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "category": {"type": "string", "enum": list(CATEGORIES), "description": "Optional category filter."},
            "limit": {"type": "integer", "minimum": 1, "maximum": MAX_LIST_LIMIT, "default": DEFAULT_LIST_LIMIT, "description": "Max items to return."},
            "offset": {"type": "integer", "minimum": 0, "maximum": 1000, "default": 0, "description": "Items to skip."},
        },
        "required": [],
        "additionalProperties": False,
    },
    handler=list_available_items,
)

GET_METADATA = ToolSpec(
    name="get_metadata",
    description="Get the full metadata record (price, stock, sale flag, tags, updated date) for one item id.",
    input_schema={
        "type": "object",
        "properties": {
            "item_id": {"type": "string", "pattern": ITEM_ID_PATTERN, "maxLength": 16, "description": "Item id such as 'book-001'."},
        },
        "required": ["item_id"],
        "additionalProperties": False,
    },
    handler=get_metadata,
)

CHECK_CONDITION = ToolSpec(
    name="check_condition",
    description=(
        "Check one named condition for an item: in_stock, on_sale, low_stock "
        "(optional threshold, default 5), or price_below (threshold required)."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "item_id": {"type": "string", "pattern": ITEM_ID_PATTERN, "maxLength": 16, "description": "Item id such as 'book-001'."},
            "condition": {"type": "string", "enum": list(CONDITIONS), "description": "Condition to evaluate."},
            "threshold": {"type": "number", "minimum": 0, "maximum": 1000000, "description": "Used by low_stock and price_below only."},
        },
        "required": ["item_id", "condition"],
        "additionalProperties": False,
    },
    handler=check_condition,
)

ALL_TOOLS: Tuple[ToolSpec, ...] = (LIST_AVAILABLE_ITEMS, GET_METADATA, CHECK_CONDITION)
