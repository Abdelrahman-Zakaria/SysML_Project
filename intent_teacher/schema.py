"""Hand-written validator for the `intent.v1` document. Stdlib only.

An intent describes WHAT a project request wants. It is data, never code:
unknown keys are rejected and string fields that look like code are rejected.
"""
import json
import re

SCHEMA_VERSION = "intent.v1"
PROJECT_TYPES = {"web_app", "data_pipeline", "cli_tool", "mobile_app", "automation", "other"}
RISK_LEVELS = {"low", "medium", "high"}
TOP_KEYS = {
    "schema_version", "project_type", "goal", "components", "constraints",
    "risk_level", "needs_clarification", "clarifying_questions",
}
COMPONENT_KEYS = {"name", "purpose"}

# Heuristic guard: the teacher must describe intent, not smuggle in code.
_CODE_PATTERNS = [
    re.compile(r"```"),
    re.compile(r"^#!", re.M),
    re.compile(r"^\s*(import\s+\w|from\s+\w+\s+import\s|def\s+\w+\(|class\s+\w+[:(])", re.M),
]


class InvalidJSONError(ValueError):
    """Model output was not a single parseable JSON document."""


class IntentValidationError(ValueError):
    """JSON parsed but does not satisfy intent.v1."""

    def __init__(self, errors):
        self.errors = list(errors)
        super().__init__("; ".join(self.errors))


def parse_intent_json(text):
    """Strict parse: the whole reply must be JSON (no prose, no code fences)."""
    if not isinstance(text, str) or not text.strip():
        raise InvalidJSONError("empty model output")
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError as exc:
        raise InvalidJSONError(f"not valid JSON: {exc}") from exc


def _str(errors, path, value, max_len):
    if not isinstance(value, str):
        errors.append(f"{path}: expected string")
        return
    if not value.strip():
        errors.append(f"{path}: must not be empty")
    if len(value) > max_len:
        errors.append(f"{path}: longer than {max_len} characters")
    if any(p.search(value) for p in _CODE_PATTERNS):
        errors.append(f"{path}: looks like code, intents must be plain descriptions")


def _str_list(errors, path, value, max_items, max_len, min_items=0):
    if not isinstance(value, list):
        errors.append(f"{path}: expected list")
        return
    if not (min_items <= len(value) <= max_items):
        errors.append(f"{path}: needs {min_items}-{max_items} items, got {len(value)}")
    for i, item in enumerate(value):
        _str(errors, f"{path}[{i}]", item, max_len)


def validate_intent(obj):
    """Return `obj` if valid, else raise IntentValidationError listing every problem."""
    errors = []
    if not isinstance(obj, dict):
        raise IntentValidationError(["root: expected JSON object"])

    for key in sorted(TOP_KEYS - obj.keys()):
        errors.append(f"missing key: {key}")
    for key in sorted(obj.keys() - TOP_KEYS):
        errors.append(f"unexpected key: {key}")

    if "schema_version" in obj and obj["schema_version"] != SCHEMA_VERSION:
        errors.append(f"schema_version: expected {SCHEMA_VERSION!r}, got {obj['schema_version']!r}")
    if "project_type" in obj and obj["project_type"] not in PROJECT_TYPES:
        errors.append(f"project_type: must be one of {sorted(PROJECT_TYPES)}")
    if "risk_level" in obj and obj["risk_level"] not in RISK_LEVELS:
        errors.append(f"risk_level: must be one of {sorted(RISK_LEVELS)}")
    if "goal" in obj:
        _str(errors, "goal", obj["goal"], 300)

    if "components" in obj:
        comps = obj["components"]
        if not isinstance(comps, list) or not (1 <= len(comps) <= 10):
            errors.append("components: expected list of 1-10 items")
        else:
            for i, comp in enumerate(comps):
                if not isinstance(comp, dict):
                    errors.append(f"components[{i}]: expected object")
                    continue
                for key in sorted(COMPONENT_KEYS - comp.keys()):
                    errors.append(f"components[{i}]: missing key {key}")
                for key in sorted(comp.keys() - COMPONENT_KEYS):
                    errors.append(f"components[{i}]: unexpected key {key}")
                for key in COMPONENT_KEYS & comp.keys():
                    _str(errors, f"components[{i}].{key}", comp[key], 200)

    if "constraints" in obj:
        _str_list(errors, "constraints", obj["constraints"], 10, 200)

    nc = obj.get("needs_clarification")
    if "needs_clarification" in obj and not isinstance(nc, bool):
        errors.append("needs_clarification: expected boolean")
    if "clarifying_questions" in obj:
        _str_list(errors, "clarifying_questions", obj["clarifying_questions"], 5, 200)
        qs = obj["clarifying_questions"]
        if isinstance(nc, bool) and isinstance(qs, list):
            if nc and not qs:
                errors.append("clarifying_questions: required when needs_clarification is true")
            if not nc and qs:
                errors.append("clarifying_questions: must be empty when needs_clarification is false")

    if errors:
        raise IntentValidationError(errors)
    return obj
