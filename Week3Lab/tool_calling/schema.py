"""A tiny, strict validator for the JSON Schema subset our tools use.

Supported keywords (object schemas only):
  type: "object" at the top level; properties of type
        "string" | "integer" | "number" | "boolean"
  properties, required, additionalProperties (must be False)
  enum, minimum, maximum, minLength, maxLength, pattern, default

Deliberately small: no $ref, no oneOf, no nesting. Easy to read and audit.
"""

import math
import re
from typing import Any, Dict

from .errors import (
    INVALID_TYPE,
    INVALID_VALUE,
    MISSING_ARGUMENT,
    UNEXPECTED_ARGUMENT,
    ToolError,
)

_SUPPORTED_TYPES = ("string", "integer", "number", "boolean")


def _type_name(value: Any) -> str:
    return type(value).__name__


def _check_type(name: str, value: Any, expected: str) -> None:
    # bool is a subclass of int in Python, so it must be excluded explicitly.
    if expected == "string":
        ok = isinstance(value, str)
    elif expected == "integer":
        ok = isinstance(value, int) and not isinstance(value, bool)
    elif expected == "number":
        ok = isinstance(value, (int, float)) and not isinstance(value, bool)
    elif expected == "boolean":
        ok = isinstance(value, bool)
    else:  # pragma: no cover - guarded by validate_schema_definition
        raise ValueError(f"Unsupported schema type: {expected}")
    if not ok:
        raise ToolError(
            INVALID_TYPE,
            f"Argument '{name}' must be of type {expected}, got {_type_name(value)}.",
        )


def _check_value(name: str, value: Any, spec: Dict[str, Any]) -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise ToolError(INVALID_VALUE, f"Argument '{name}' must be a finite number.")
    if "enum" in spec and value not in spec["enum"]:
        allowed = ", ".join(repr(v) for v in spec["enum"])
        raise ToolError(
            INVALID_VALUE, f"Argument '{name}' must be one of: {allowed}."
        )
    if "minimum" in spec and value < spec["minimum"]:
        raise ToolError(
            INVALID_VALUE, f"Argument '{name}' must be >= {spec['minimum']}."
        )
    if "maximum" in spec and value > spec["maximum"]:
        raise ToolError(
            INVALID_VALUE, f"Argument '{name}' must be <= {spec['maximum']}."
        )
    if isinstance(value, str):
        if "minLength" in spec and len(value) < spec["minLength"]:
            raise ToolError(
                INVALID_VALUE,
                f"Argument '{name}' must have at least {spec['minLength']} character(s).",
            )
        if "maxLength" in spec and len(value) > spec["maxLength"]:
            raise ToolError(
                INVALID_VALUE,
                f"Argument '{name}' must have at most {spec['maxLength']} character(s).",
            )
        if "pattern" in spec and re.fullmatch(spec["pattern"], value) is None:
            raise ToolError(
                INVALID_VALUE,
                f"Argument '{name}' does not match the required format.",
            )


def validate_schema_definition(schema: Dict[str, Any]) -> None:
    """Fail fast (at registration time) if a tool's own schema is malformed."""
    if schema.get("type") != "object":
        raise ValueError("Tool input schema must have type 'object'.")
    if schema.get("additionalProperties") is not False:
        raise ValueError("Tool input schema must set additionalProperties to False.")
    props = schema.get("properties")
    if not isinstance(props, dict):
        raise ValueError("Tool input schema must define 'properties'.")
    for prop_name, spec in props.items():
        if spec.get("type") not in _SUPPORTED_TYPES:
            raise ValueError(f"Property '{prop_name}' has an unsupported type.")
    for req in schema.get("required", []):
        if req not in props:
            raise ValueError(f"Required property '{req}' is not defined.")


def validate_arguments(schema: Dict[str, Any], arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Validate `arguments` against `schema`; return a new dict with defaults applied.

    Check order (so errors are predictable): extra -> missing -> type -> value.
    """
    props = schema["properties"]

    extra = sorted(set(arguments) - set(props))
    if extra:
        raise ToolError(
            UNEXPECTED_ARGUMENT,
            "Unexpected argument(s): " + ", ".join(repr(e) for e in extra) + ".",
        )

    missing = [r for r in schema.get("required", []) if r not in arguments]
    if missing:
        raise ToolError(
            MISSING_ARGUMENT,
            "Missing required argument(s): " + ", ".join(repr(m) for m in missing) + ".",
        )

    for name, value in arguments.items():
        _check_type(name, value, props[name]["type"])
    for name, value in arguments.items():
        _check_value(name, value, props[name])

    normalized = dict(arguments)
    for name, spec in props.items():
        if name not in normalized and "default" in spec:
            normalized[name] = spec["default"]
    return normalized
