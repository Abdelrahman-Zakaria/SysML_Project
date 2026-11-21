"""Structured result envelope returned by every dispatch (success or failure)."""

from dataclasses import dataclass
from typing import Any, Dict, Optional

from .errors import ErrorInfo


@dataclass(frozen=True)
class ToolResult:
    """Uniform envelope: exactly one of `data` / `error` is set."""

    tool: Optional[str]
    ok: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[ErrorInfo] = None

    @classmethod
    def success(cls, tool: str, data: Dict[str, Any]) -> "ToolResult":
        return cls(tool=tool, ok=True, data=data, error=None)

    @classmethod
    def failure(cls, tool: Optional[str], code: str, message: str) -> "ToolResult":
        return cls(tool=tool, ok=False, data=None, error=ErrorInfo(code, message))

    def to_dict(self) -> Dict[str, Any]:
        """JSON-serializable form (what would be sent back to a model)."""
        return {
            "tool": self.tool,
            "ok": self.ok,
            "data": self.data,
            "error": None
            if self.error is None
            else {"code": self.error.code, "message": self.error.message},
        }
