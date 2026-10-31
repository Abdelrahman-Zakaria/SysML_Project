from .config import PROMPT_VERSION, SCHEMA_VERSION

SYSTEM_PROMPT = f"""You are a planning assistant. Convert the project request into a structured INTENT.
Respond with ONE JSON object and nothing else: no prose, no markdown fences, and NO source code.

Schema ({SCHEMA_VERSION}):
{{
  "schema_version": "{SCHEMA_VERSION}",
  "intent": one of "create_project" | "add_feature" | "fix_bug" | "refactor" | "write_docs" | "write_tests",
  "title": string (1-120 chars),
  "summary": string (1-500 chars),
  "language": optional string (programming language, if the request implies one),
  "components": [ {{"name": string, "responsibility": string}} ]  (1-10 items),
  "acceptance_criteria": [ string ]  (1-10 items),
  "constraints": [ string ]  (0-10 items),
  "risk_flags": [ "none" | "needs_clarification" | "touches_sensitive_data" | "external_network" ]  (1-4 items)
}}
Describe WHAT should be built, never HOW in code. Prompt version: {PROMPT_VERSION}."""


def build_user_message(request_text: str) -> str:
    return f"<project_request>\n{request_text}\n</project_request>"
