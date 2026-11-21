"""Deterministic, read-only in-memory data the tools operate on.

No files, no network, no randomness: the same call always gives the same answer.
"""

from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass(frozen=True)
class CatalogItem:
    item_id: str
    name: str
    category: str
    price: float
    stock: int
    on_sale: bool
    tags: Tuple[str, ...]
    updated: str  # ISO date


CATEGORIES = ("books", "electronics", "stationery")

_ITEMS = (
    CatalogItem("book-001", "Python Crash Course", "books", 29.99, 14, False, ("python", "beginner"), "2026-09-01"),
    CatalogItem("book-002", "Deep Learning Basics", "books", 49.50, 3, True, ("ai", "ml"), "2026-09-12"),
    CatalogItem("book-003", "Computer Architecture", "books", 64.00, 0, False, ("hardware",), "2026-08-20"),
    CatalogItem("elec-001", "USB-C Cable 1m", "electronics", 7.25, 120, False, ("cable", "usb"), "2026-10-02"),
    CatalogItem("elec-002", "Mechanical Keyboard", "electronics", 89.90, 5, True, ("keyboard",), "2026-10-05"),
    CatalogItem("elec-003", "Wireless Mouse", "electronics", 19.99, 0, False, ("mouse",), "2026-07-30"),
    CatalogItem("stat-001", "Graph Notebook A4", "stationery", 3.50, 60, False, ("notebook",), "2026-09-18"),
    CatalogItem("stat-002", "Gel Pen Set (10)", "stationery", 6.75, 4, True, ("pen",), "2026-10-10"),
)

_BY_ID = {item.item_id: item for item in _ITEMS}


def all_items() -> Tuple[CatalogItem, ...]:
    """Every item, in a fixed order (sorted by id)."""
    return tuple(sorted(_ITEMS, key=lambda i: i.item_id))


def find_item(item_id: str) -> Optional[CatalogItem]:
    return _BY_ID.get(item_id)
