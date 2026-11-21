import json
from pathlib import Path
from pydantic import BaseModel, Field, ValidationError

MODEL_PATH = Path(__file__).parent / "sysml_model.json"


def load_model(path: Path = MODEL_PATH) -> dict:
    """Reads the local JSON SysML model into a Python dictionary."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


class ElementIdInput(BaseModel):
    element_id: str = Field(..., pattern=r"^(REQ|BLK)-\d{3}$")


class CheckMassInput(BaseModel):
    target_id: str = Field(..., pattern=r"^BLK-\d{3}$")
    proposed_mass_kg: float = Field(..., gt=0)


def list_elements() -> dict:
    """Returns all valid element IDs in the SysML model."""
    model = load_model()
    return {"status": "ok", "elements": list(model.keys())}


def get_element_details(args: ElementIdInput) -> dict:
    """Fetches metadata for one element by ID, or returns NOT_FOUND."""
    model = load_model()
    item = model.get(args.element_id)

    if item is None:
        return {
            "status": "error",
            "code": "NOT_FOUND",
            "message": f"Element '{args.element_id}' does not exist in the model.",
        }

    return {"status": "ok", "element_id": args.element_id, "data": item}


def validate_operation(args: CheckMassInput) -> dict:
    """Checks if a proposed block mass satisfies requirement REQ-101."""
    model = load_model()

    block = model.get(args.target_id)
    if block is None:
        return {
            "status": "error",
            "code": "NOT_FOUND",
            "message": f"Block '{args.target_id}' does not exist in the model.",
        }

    requirement = model.get("REQ-101")
    if requirement is None:
        return {
            "status": "error",
            "code": "NOT_FOUND",
            "message": "Requirement 'REQ-101' is missing from the model.",
        }

    limit = requirement["max_mass_kg"]
    passed = args.proposed_mass_kg <= limit

    return {
        "status": "ok",
        "target_id": args.target_id,
        "valid": passed,
        "proposed_mass_kg": args.proposed_mass_kg,
        "max_allowed_kg": limit,
    }


ALLOWED_TOOLS = {
    "list_elements": (None, list_elements),
    "get_element_details": (ElementIdInput, get_element_details),
    "validate_operation": (CheckMassInput, validate_operation),
}


def dispatch_tool(tool_name: str, raw_args: dict) -> dict:
    """Validates tool name and arguments before running any local function."""
    if tool_name not in ALLOWED_TOOLS:
        return {
            "status": "error",
            "code": "UNKNOWN_TOOL",
            "message": f"Tool '{tool_name}' is not allowed.",
        }

    schema, func = ALLOWED_TOOLS[tool_name]

    try:
        if schema is None:
            return func()
        validated_args = schema(**raw_args)
        return func(validated_args)
    except ValidationError as e:
        return {
            "status": "error",
            "code": "INVALID_ARGS",
            "message": e.errors()[0]["msg"],
        }
    except Exception as e:
        return {
            "status": "error",
            "code": "TOOL_ERROR",
            "message": f"Tool crashed: {str(e)}",
        }