"""Tool registry (allowlist) and dispatcher.

The dispatcher is the ONLY door to the tools. It never looks anything up by
getattr/import/eval: a name is either a key in the registry dict or rejected.
"""

import json
from typing import Any, Dict, Iterable, List, Optional

from .errors import (
    INTERNAL_ERROR,
    INVALID_CALL_FORMAT,
    UNKNOWN_TOOL,
    ToolError,
)
from .results import ToolResult
from .schema import validate_arguments, validate_schema_definition
from .tools import ALL_TOOLS, ToolSpec

MAX_TOOL_NAME_LENGTH = 64
MAX_RAW_CALL_CHARS = 10_000


class ToolRegistry:
    """Allowlist of tools, keyed by exact name."""

    def __init__(self, tools: Iterable[ToolSpec] = ()) -> None:
        self._tools: Dict[str, ToolSpec] = {}
        for spec in tools:
            self.register(spec)

    def register(self, spec: ToolSpec) -> None:
        if not spec.name or len(spec.name) > MAX_TOOL_NAME_LENGTH:
            raise ValueError("Tool name must be 1-64 characters.")
        if spec.name in self._tools:
            raise ValueError(f"Tool '{spec.name}' is already registered.")
        if not callable(spec.handler):
            raise ValueError(f"Tool '{spec.name}' has a non-callable handler.")
        validate_schema_definition(spec.input_schema)
        self._tools[spec.name] = spec

    def get(self, name: str) -> Optional[ToolSpec]:
        return self._tools.get(name)

    def names(self) -> List[str]:
        return sorted(self._tools)

    def describe(self) -> List[Dict[str, Any]]:
        """Tool definitions in the shape a model API expects (name/description/schema)."""
        return [
            {"name": s.name, "description": s.description, "input_schema": s.input_schema}
            for s in (self._tools[n] for n in self.names())
        ]


def build_default_registry() -> ToolRegistry:
    return ToolRegistry(ALL_TOOLS)


def _to_data(value: Any) -> Dict[str, Any]:
    if hasattr(value, "to_dict"):
        return value.to_dict()
    raise TypeError("Tool handlers must return a typed result with to_dict().")


class ToolDispatcher:
    """Validates a model-style call and runs the matching tool. Never raises."""

    def __init__(self, registry: Optional[ToolRegistry] = None) -> None:
        self.registry = registry if registry is not None else build_default_registry()

    def dispatch(self, call: Any) -> ToolResult:
        """`call` must look like {"name": str, "arguments": dict}."""
        name: Optional[str] = None
        try:
            if not isinstance(call, dict):
                raise ToolError(INVALID_CALL_FORMAT, "Tool call must be an object.")
            extra_keys = set(call) - {"name", "arguments"}
            if extra_keys:
                raise ToolError(
                    INVALID_CALL_FORMAT,
                    "Tool call may only contain 'name' and 'arguments'.",
                )
            raw_name = call.get("name")
            if not isinstance(raw_name, str) or not raw_name:
                raise ToolError(INVALID_CALL_FORMAT, "Tool call needs a non-empty string 'name'.")
            name = raw_name[:MAX_TOOL_NAME_LENGTH]
            arguments = call.get("arguments", {})
            if not isinstance(arguments, dict):
                raise ToolError(INVALID_CALL_FORMAT, "'arguments' must be an object.")
            if not all(isinstance(k, str) for k in arguments):
                raise ToolError(INVALID_CALL_FORMAT, "Argument names must be strings.")

            spec = self.registry.get(raw_name)
            if spec is None:
                raise ToolError(UNKNOWN_TOOL, f"Tool '{name}' is not allowed.")

            clean = validate_arguments(spec.input_schema, arguments)
            return ToolResult.success(spec.name, _to_data(spec.handler(**clean)))
        except ToolError as exc:
            return ToolResult.failure(name, exc.code, exc.message)
        except Exception:  # noqa: BLE001 - last-resort guard; details are not leaked
            return ToolResult.failure(name, INTERNAL_ERROR, "Unexpected internal error.")

    def dispatch_json(self, raw: Any) -> ToolResult:
        """Same as dispatch(), but takes the raw JSON text a model would emit."""
        if not isinstance(raw, str):
            return ToolResult.failure(None, INVALID_CALL_FORMAT, "Raw tool call must be a string.")
        if len(raw) > MAX_RAW_CALL_CHARS:
            return ToolResult.failure(None, INVALID_CALL_FORMAT, "Raw tool call is too large.")
        try:
            call = json.loads(raw)
        except (ValueError, RecursionError):
            return ToolResult.failure(None, INVALID_CALL_FORMAT, "Tool call is not valid JSON.")
        return self.dispatch(call)
