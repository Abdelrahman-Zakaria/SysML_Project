"""Stable error codes and the single exception type used by the tool layer."""

from dataclasses import dataclass

# Stable, machine-readable codes. A model (Iteration 2) can branch on these.
UNKNOWN_TOOL = "UNKNOWN_TOOL"
INVALID_CALL_FORMAT = "INVALID_CALL_FORMAT"
MISSING_ARGUMENT = "MISSING_ARGUMENT"
UNEXPECTED_ARGUMENT = "UNEXPECTED_ARGUMENT"
INVALID_TYPE = "INVALID_TYPE"
INVALID_VALUE = "INVALID_VALUE"
NOT_FOUND = "NOT_FOUND"
INTERNAL_ERROR = "INTERNAL_ERROR"

ALL_ERROR_CODES = frozenset(
    {
        UNKNOWN_TOOL,
        INVALID_CALL_FORMAT,
        MISSING_ARGUMENT,
        UNEXPECTED_ARGUMENT,
        INVALID_TYPE,
        INVALID_VALUE,
        NOT_FOUND,
        INTERNAL_ERROR,
    }
)


class ToolError(Exception):
    """Raised anywhere in the tool layer; always carries a stable code."""

    def __init__(self, code: str, message: str) -> None:
        if code not in ALL_ERROR_CODES:
            raise ValueError(f"Unknown error code: {code!r}")
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class ErrorInfo:
    """Serializable description of a failure."""

    code: str
    message: str
