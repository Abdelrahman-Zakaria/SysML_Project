"""Strict local validation of the teacher's output. Output is DATA (an intent), never code to run."""
import json
import re

from .config import SCHEMA_VERSION

INTENTS = {"create_project", "add_feature", "fix_bug", "refactor", "write_docs", "write_tests"}
RISK_FLAGS = {"none", "needs_clarification", "touches_sensitive_data", "external_network"}
REQUIRED = {"schema_version", "intent", "title", "summary", "components", "acceptance_criteria",
            "constraints", "risk_flags"}
OPTIONAL = {"language"}

# Heuristic guard: the intent must describe work, not contain executable code.
_CODE_PATTERNS = [
    re.compile(r"```"),
    re.compile(r"^\s*#!", re.M),
    re.compile(r"^\s*def\s+\w+\s*\(", re.M),
    re.compile(r"^\s*import\s+[\w.]+\s*$", re.M),
    re.compile(r"^\s*from\s+\S+\s+import\b", re.M),
    re.compile(r"<script", re.I),
    re.compile(r"\b(subprocess|os\.system|eval\(|exec\()"),
    re.compile(r"\brm\s+-rf\b"),
]


class InvalidJSON(ValueError):
    pass


class SchemaViolation(ValueError):
    pass


def _str(value, field, lo, hi):
    if not isinstance(value, str):
        raise SchemaViolation(f"{field}: expected string, got {type(value).__name__}")
    if not (lo <= len(value.strip()) and len(value) <= hi):
        raise SchemaViolation(f"{field}: length must be {lo}-{hi}")
    for pat in _CODE_PATTERNS:
        if pat.search(value):
            raise SchemaViolation(f"{field}: looks like executable code (matched {pat.pattern!r})")
    return value


def _list(value, field, lo, hi):
    if not isinstance(value, list):
        raise SchemaViolation(f"{field}: expected list, got {type(value).__name__}")
    if not (lo <= len(value) <= hi):
        raise SchemaViolation(f"{field}: must have {lo}-{hi} items, got {len(value)}")
    return value


def validate_intent(data) -> dict:
    if not isinstance(data, dict):
        raise SchemaViolation(f"top level must be an object, got {type(data).__name__}")
    missing = REQUIRED - data.keys()
    if missing:
        raise SchemaViolation(f"missing fields: {sorted(missing)}")
    extra = data.keys() - REQUIRED - OPTIONAL
    if extra:
        raise SchemaViolation(f"unexpected fields: {sorted(extra)}")
    if data["schema_version"] != SCHEMA_VERSION:
        raise SchemaViolation(f"schema_version must be {SCHEMA_VERSION!r}, got {data['schema_version']!r}")
    if data["intent"] not in INTENTS:
        raise SchemaViolation(f"intent: {data['intent']!r} not in {sorted(INTENTS)}")
    _str(data["title"], "title", 1, 120)
    _str(data["summary"], "summary", 1, 500)
    if "language" in data:
        _str(data["language"], "language", 1, 40)
    for i, comp in enumerate(_list(data["components"], "components", 1, 10)):
        if not isinstance(comp, dict) or set(comp) != {"name", "responsibility"}:
            raise SchemaViolation(f"components[{i}]: must be an object with exactly name, responsibility")
        _str(comp["name"], f"components[{i}].name", 1, 80)
        _str(comp["responsibility"], f"components[{i}].responsibility", 1, 300)
    for i, s in enumerate(_list(data["acceptance_criteria"], "acceptance_criteria", 1, 10)):
        _str(s, f"acceptance_criteria[{i}]", 1, 300)
    for i, s in enumerate(_list(data["constraints"], "constraints", 0, 10)):
        _str(s, f"constraints[{i}]", 1, 300)
    for i, flag in enumerate(_list(data["risk_flags"], "risk_flags", 1, 4)):
        if flag not in RISK_FLAGS:
            raise SchemaViolation(f"risk_flags[{i}]: {flag!r} not in {sorted(RISK_FLAGS)}")
    return data


def parse_intent(text: str) -> dict:
    """Strict: the raw output must be a JSON document. Markdown-fenced JSON is rejected on purpose."""
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError) as e:
        raise InvalidJSON(f"output is not valid JSON: {e}") from e
    return validate_intent(data)
