"""Tool / Function Calling layer (Week 3, Iteration 1).

Public API:
    ToolDispatcher, ToolRegistry, build_default_registry, ToolResult, ToolError
"""

from .errors import ToolError
from .registry import ToolDispatcher, ToolRegistry, build_default_registry
from .results import ToolResult

__all__ = ["ToolDispatcher", "ToolRegistry", "build_default_registry", "ToolResult", "ToolError"]
