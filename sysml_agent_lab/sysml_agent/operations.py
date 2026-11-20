"""Milestone 1 - the typed operations propose_operation understands."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AddRequirement:
    id: str
    name: str
    text: str
    domain: str


@dataclass(frozen=True)
class AddSatisfy:
    requirement_id: str
    part_id: str


@dataclass(frozen=True)
class RenameElement:
    element_id: str
    new_name: str


SUPPORTED_OPERATIONS = (AddRequirement, AddSatisfy, RenameElement)
