import json
import os
import re
from pathlib import Path
from typing import Any, Callable, Optional
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# ==============================================================================
# 1. (External SysML v2 File & Deterministic Parser)
# ==============================================================================
DEFAULT_MODEL_PATH = Path(__file__).resolve().parent / "system_model.sysml"
MODEL_PATH = Path(os.getenv("SYSML_MODEL_PATH", str(DEFAULT_MODEL_PATH)))


def parse_sysml_model(source_text: str) -> dict[str, dict[str, Any]]:
    elements: dict[str, dict[str, Any]] = {}
    block_re = re.compile(r"\b(part def|requirement def)\s+([A-Za-z_]\w*)\s*\{([^}]*)\}")
    attr_re = re.compile(r"\battribute\s+([A-Za-z_]\w*)\s*:\s*([A-Za-z_]\w*)(?:\s*=\s*\"?([^\";]+)\"?)?\s*;")
    req_re = re.compile(r"\brequire\s+constraint\s*\{([^}]+)\}")

    for kind, name, body in block_re.findall(source_text):
        attrs, status = {}, "UNKNOWN"
        for a_name, a_type, val in attr_re.findall(body):
            clean_val = val.strip() if val else None
            attrs[a_name] = {"type": a_type, "value": clean_val}
            if a_name == "status" and clean_val:
                status = clean_val
        elements[name] = {
            "kind": kind,
            "attributes": attrs,
            "constraints": [c.strip() for c in req_re.findall(body)],
            "status": status,
        }
    return elements


def load_parsed_model(path: Path = MODEL_PATH) -> dict[str, dict[str, Any]]:
    """Reads and parses the external .sysml file on demand."""
    if not path.is_file():
        raise FileNotFoundError(f"SysML file not found at: {path}")
    return parse_sysml_model(path.read_text(encoding="utf-8"))


ALLOWED_KINDS = {"all", "part def", "requirement def"}
ALLOWED_STATUSES = {"ACTIVE", "DRAFT", "VERIFIED"}
ALLOWED_TYPES = {"Real", "Integer", "Boolean", "String"}


def _is_valid_id(val: Any) -> bool:
    return isinstance(val, str) and val.strip().isidentifier()


# ==============================================================================
# 2. (Deterministic Inspection Tools)
# ==============================================================================
def list_available_items(kind_filter: str = "all") -> dict[str, Any]:
    if not isinstance(kind_filter, str) or kind_filter not in ALLOWED_KINDS:
        return {"ok": False, "error_code": "INVALID_ARGUMENT", "message": f"Invalid kind_filter: {kind_filter!r}"}
    model = load_parsed_model()
    items = [
        {"name": k, "kind": v["kind"]}
        for k, v in model.items()
        if kind_filter == "all" or v["kind"] == kind_filter
    ]
    return {"ok": True, "items": items}


def get_metadata(item_name: str) -> dict[str, Any]:
    if not _is_valid_id(item_name):
        return {"ok": False, "error_code": "INVALID_ARGUMENT", "message": f"Invalid identifier: {item_name!r}"}
    model = load_parsed_model()
    name = item_name.strip()
    if name not in model:
        return {"ok": False, "error_code": "NO_EVIDENCE", "message": f"Element '{name}' not found in {MODEL_PATH.name}."}
    return {"ok": True, "item_name": name, "metadata": model[name]}


def check_condition(item_name: str, expected_status: str) -> dict[str, Any]:
    if not _is_valid_id(item_name) or not isinstance(expected_status, str) or expected_status not in ALLOWED_STATUSES:
        return {"ok": False, "error_code": "INVALID_ARGUMENT", "message": "Invalid item_name or expected_status."}
    model = load_parsed_model()
    name = item_name.strip()
    if name not in model:
        return {"ok": False, "error_code": "NO_EVIDENCE", "message": f"Element '{name}' not found in {MODEL_PATH.name}."}
    actual = model[name]["status"]
    return {
        "ok": True,
        "item_name": name,
        "expected_status": expected_status,
        "actual_status": actual,
        "condition_met": actual == expected_status,
    }


INSPECTION_TOOLS: dict[str, Callable[..., dict[str, Any]]] = {
    "list_available_items": list_available_items,
    "get_metadata": get_metadata,
    "check_condition": check_condition,
}

# ==============================================================================
# 3. (SysML Typed Operation Validator)
# ==============================================================================
def compile_and_validate_sysml(
    operation: str,
    target_element: str,
    member_name: str,
    sysml_type: str = "",
    expression: Optional[str] = None,
    evidence_log: Optional[list[dict[str, Any]]] = None,
) -> dict[str, Any]:
    if not evidence_log:
        return {"ok": False, "error_code": "NO_EVIDENCE", "message": "Model inspection required before proposing edits."}
    if operation not in {"add_attribute", "add_constraint"} or not _is_valid_id(member_name) or sysml_type not in ALLOWED_TYPES:
        return {"ok": False, "error_code": "INVALID_ARGUMENT", "message": "Invalid operation, identifier, or SysML type."}

    model = load_parsed_model()
    if not isinstance(target_element, str) or target_element not in model:
        return {"ok": False, "error_code": "NO_EVIDENCE", "message": f"Target '{target_element}' not in {MODEL_PATH.name}."}

    elem = model[target_element]
    if operation == "add_attribute":
        if member_name in elem["attributes"]:
            return {"ok": False, "error_code": "VALIDATION_REJECTED", "message": f"Duplicate attribute '{member_name}'."}
        snippet = f"{elem['kind']} {target_element} {{\n    attribute {member_name} : {sysml_type};\n}}"
        return {"ok": True, "compiled_sysml": snippet}

    if elem["kind"] != "requirement def" or sysml_type != "Boolean":
        return {"ok": False, "error_code": "VALIDATION_REJECTED", "message": "Constraints require a requirement def and Boolean type."}
    if not isinstance(expression, str) or not expression.strip():
        return {"ok": False, "error_code": "INVALID_ARGUMENT", "message": "Constraint requires a boolean expression."}

    snippet = f"requirement def {target_element} {{\n    require constraint {member_name} {{ {expression.strip()} }}\n}}"
    return {"ok": True, "compiled_sysml": snippet}


# ==============================================================================
# 4. (Tool Schemas)
# ==============================================================================
TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "list_available_items",
            "description": "List available elements in the SysML v2 file.",
            "parameters": {
                "type": "object",
                "properties": {"kind_filter": {"type": "string", "enum": ["all", "part def", "requirement def"]}},
                "required": ["kind_filter"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_metadata",
            "description": "Get attributes, constraints, kind, and status of a SysML element.",
            "parameters": {
                "type": "object",
                "properties": {"item_name": {"type": "string"}},
                "required": ["item_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_condition",
            "description": "Check if a SysML element matches an expected lifecycle status.",
            "parameters": {
                "type": "object",
                "properties": {
                    "item_name": {"type": "string"},
                    "expected_status": {"type": "string", "enum": ["ACTIVE", "DRAFT", "VERIFIED"]},
                },
                "required": ["item_name", "expected_status"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "propose_typed_operation",
            "description": "Submit a typed SysML modification candidate to the validator after inspecting the model.",
            "parameters": {
                "type": "object",
                "properties": {
                    "operation": {"type": "string", "enum": ["add_attribute", "add_constraint"]},
                    "target_element": {"type": "string"},
                    "member_name": {"type": "string"},
                    "sysml_type": {
                        "type": "string",
                        "enum": ["Real", "Integer", "Boolean", "String"],
                        "description": "Required data type. Always pass 'Boolean' when operation is 'add_constraint'.",
                    },
                    "expression": {"type": "string"},
                },
                "required": ["operation", "target_element", "member_name"],
            },
        },
    },
]

# ==============================================================================
# 5. Agent (Agent Loop & Exit Gate)
# ==============================================================================
def build_default_llm_fn() -> Callable[[list[dict[str, Any]]], Any]:
    provider = os.getenv("PROVIDER", "groq").lower()
    model_id = os.getenv("MODEL_ID", "openai/gpt-oss-120b")
    base_url = "https://api.groq.com/openai/v1" if provider == "groq" else "https://router.huggingface.co/v1"
    api_key = os.environ["GROQ_API_KEY"] if provider == "groq" else os.environ["HF_TOKEN"]
    client = OpenAI(base_url=base_url, api_key=api_key)

    return lambda msgs: client.chat.completions.create(
        model=model_id, messages=msgs, tools=TOOLS_SCHEMA, tool_choice="auto", temperature=0.0
    ).choices[0].message


def run_agent(
    user_prompt: str,
    llm_fn: Optional[Callable[[list[dict[str, Any]]], Any]] = None,
    max_calls: int = 5,
    tool_registry: Optional[dict[str, Callable[..., dict[str, Any]]]] = None,
) -> dict[str, Any]:
    active_llm = llm_fn or build_default_llm_fn()
    active_tools = tool_registry if tool_registry is not None else INSPECTION_TOOLS
    messages: list[dict[str, Any]] = [
        {
            "role": "system",
            "content": (
                "You are a strict SysML v2 assistant. Inspect the model with tools before making claims "
                "or proposing operations. If an element is missing, state there is no evidence."
            ),
        },
        {"role": "user", "content": user_prompt},
    ]

    evidence_log, trace = [], []
    calls_used, last_val = 0, None
    had_fabricated = had_failure = False

    while calls_used < max_calls:
        msg = active_llm(messages)
        tool_calls = getattr(msg, "tool_calls", None)
        entry: dict[str, Any] = {"role": "assistant", "content": getattr(msg, "content", None) or ""}
        if tool_calls:
            entry["tool_calls"] = [
                {"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                for tc in tool_calls
            ]
        messages.append(entry)

        if not tool_calls:
            if last_val is not None and not last_val.get("ok"):
                return {"status": "REJECTED", "reason": last_val["message"], "error_code": last_val["error_code"], "evidence_count": len(evidence_log), "trace": trace}
            if had_fabricated and not evidence_log:
                return {"status": "FAILED", "error_code": "FABRICATED_TOOL", "reason": "Fabricated tool rejected.", "evidence_count": 0, "trace": trace}
            if had_failure and not evidence_log:
                return {"status": "FAILED", "error_code": "TOOL_FAILURE", "reason": "Tool runtime failure.", "evidence_count": 0, "trace": trace}
            if not evidence_log:
                return {"status": "NO_EVIDENCE", "reason": "No verified evidence retrieved.", "evidence_count": 0, "trace": trace}
            return {
                "status": "SUCCESS",
                "answer": entry["content"],
                "validated_sysml": last_val.get("compiled_sysml") if last_val else None,
                "evidence_count": len(evidence_log),
                "trace": trace,
            }

        for tc in tool_calls:
            calls_used += 1
            if calls_used > max_calls:
                return {"status": "FAILED", "error_code": "MAX_CALLS_EXCEEDED", "reason": f"Limit ({max_calls}) exceeded.", "evidence_count": len(evidence_log), "trace": trace}

            fn_name, raw_args = tc.function.name, tc.function.arguments
            parsed_args: Any = raw_args
            try:
                parsed_args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                if not isinstance(parsed_args, dict):
                    raise TypeError("Arguments must be a JSON object.")
                if fn_name == "propose_typed_operation":
                    result = compile_and_validate_sysml(**parsed_args, evidence_log=evidence_log)
                    last_val = result
                elif fn_name not in active_tools:
                    had_fabricated = True
                    result = {"ok": False, "error_code": "FABRICATED_TOOL", "message": f"Unknown tool '{fn_name}'."}
                else:
                    result = active_tools[fn_name](**parsed_args)
                    if result.get("ok") is True:
                        evidence_log.append({"tool": fn_name, "args": parsed_args, "data": result})
            except (json.JSONDecodeError, TypeError) as exc:
                result = {"ok": False, "error_code": "INVALID_ARGUMENT", "message": str(exc)}
                if fn_name == "propose_typed_operation":
                    last_val = result
            except Exception as exc:
                had_failure = True
                result = {"ok": False, "error_code": "TOOL_FAILURE", "message": str(exc)}

            trace.append({"tool": fn_name, "args": parsed_args, "result": result})
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": json.dumps(result)})

    return {"status": "FAILED", "error_code": "MAX_CALLS_EXCEEDED", "reason": f"Limit ({max_calls}) reached.", "evidence_count": len(evidence_log), "trace": trace}


# ==============================================================================
# 6. (Interactive CLI)
# ==============================================================================
if __name__ == "__main__":
    show_trace = True
    print(f"SysML v2 Deterministic Agent CLI | Source file: {MODEL_PATH.name}")
    print("Commands: 'reload' (check file), 'trace' (toggle logs), 'exit' (quit)\n" + "=" * 75)

    while True:
        try:
            prompt = input("\nSysML Prompt > ").strip()
        except (KeyboardInterrupt, EOFError):
            break
        if not prompt:
            continue
        if prompt.lower() in {"exit", "quit"}:
            break
        if prompt.lower() == "trace":
            show_trace = not show_trace
            print(f"Trace display: {'ON' if show_trace else 'OFF'}")
            continue
        if prompt.lower() == "reload":
            try:
                loaded = load_parsed_model()
                print(f"Loaded {len(loaded)} elements from {MODEL_PATH.name}: {list(loaded.keys())}")
            except Exception as exc:
                print(f"File error: {exc}")
            continue

        out = run_agent(prompt, max_calls=8)
        if show_trace and out.get("trace"):
            for i, s in enumerate(out["trace"], 1):
                tag = "PASS" if s["result"].get("ok") else f"FAIL:{s['result'].get('error_code')}"
                print(f"  [{i}] [{tag}] {s['tool']}({s['args']})")
        print(f"STATUS: {out['status']} | EVIDENCE: {out['evidence_count']}")
        if out.get("validated_sysml"):
            print(f"VALIDATED SYSML:\n{out['validated_sysml']}")
        print(out.get("answer") or out.get("reason", ""))