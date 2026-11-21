# Tool / Function Calling — Iteration 1

A safe, deterministic, local tool layer: **validate → dispatch → structured result**.
No LLM, no network, no frameworks, Python standard library only (3.9+).
The Control Loop (model ↔ tools) is intentionally **not** here; it is Iteration 2.

## Architecture

```
model-style call ──► ToolDispatcher.dispatch(call)
 {"name","arguments"}      │
                           ├─ 1. call shape valid?          (INVALID_CALL_FORMAT)
                           ├─ 2. name in registry allowlist? (UNKNOWN_TOOL)
                           ├─ 3. validate_arguments(schema)  (UNEXPECTED_ARGUMENT, MISSING_ARGUMENT,
                           │                                  INVALID_TYPE, INVALID_VALUE)
                           ├─ 4. run handler(**clean_args)   (NOT_FOUND + tool-specific errors)
                           └─ 5. wrap in ToolResult          (never raises; INTERNAL_ERROR as last resort)
```

| File | Role |
|---|---|
| `tool_calling/errors.py` | Stable error codes + `ToolError` |
| `tool_calling/results.py` | `ToolResult` envelope (`ok`, `data` or `error`) |
| `tool_calling/schema.py` | Small strict JSON-Schema-subset validator |
| `tool_calling/catalog.py` | Fixed in-memory records (8 items) the tools read |
| `tool_calling/tools.py` | 3 tools: spec (name, description, schema) + handler + typed results |
| `tool_calling/registry.py` | `ToolRegistry` (allowlist) and `ToolDispatcher` |
| `demo_tool_calling.py` | Simulated model calls (valid and rejected) |
| `tests/test_tool_calling.py` | 39 `unittest` tests |

## The tools

| Tool | Arguments | Returns |
|---|---|---|
| `list_available_items` | `category?` (enum), `limit?` (1–20, default 10), `offset?` (0–1000, default 0) | page of `{item_id, name, category}` + `total`, `returned`, `offset`, `has_more` |
| `get_metadata` | `item_id` (pattern `xxx-000`) | full record: price, stock, on_sale, tags, updated |
| `check_condition` | `item_id`, `condition` (`in_stock` / `on_sale` / `low_stock` / `price_below`), `threshold?` (0–1,000,000) | `{satisfied, observed, threshold}` |

`low_stock` uses threshold default 5; `price_below` requires a threshold; `in_stock` and `on_sale` reject one.

## Error codes

`UNKNOWN_TOOL`, `INVALID_CALL_FORMAT`, `MISSING_ARGUMENT`, `UNEXPECTED_ARGUMENT`,
`INVALID_TYPE`, `INVALID_VALUE`, `NOT_FOUND`, `INTERNAL_ERROR`.

## Safety design

- **Allowlist only:** tools are dict lookups by exact name; no `getattr`, `eval`, `exec`, or dynamic imports.
- **Strict schemas:** `additionalProperties: false`; `bool` is never accepted as a number; NaN/inf rejected.
- **Bounded:** list size capped at 20, offset capped, id length/pattern limited, raw JSON capped at 10,000 chars.
- **Closed condition set:** conditions are an enum, never an expression string.
- **Never raises to the caller:** every failure becomes a `ToolResult` with a stable code; internal details are not leaked.

## Run

From the repository root:

```bash
python demo_tool_calling.py
python -m unittest discover -s tests -p "test_tool_calling.py" -v
```

Programmatic use:

```python
from tool_calling import ToolDispatcher

d = ToolDispatcher()
result = d.dispatch({"name": "get_metadata", "arguments": {"item_id": "book-001"}})
print(result.ok, result.to_dict())

d.registry.describe()   # tool definitions a model API would receive
```

## Extending (later iterations)

Add a new `ToolSpec` in `tools.py` and include it in `ALL_TOOLS`; the registry, validation,
and dispatcher need no changes. Iteration 2 will call `ToolDispatcher.dispatch` from the control loop.
