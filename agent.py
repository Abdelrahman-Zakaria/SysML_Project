"""Week 3 safe tool-calling agent lab (NVIDIA NIM Edition).

A small, bounded agent for inspecting a local Smart Elevator SysML-like model.
The tools and engineering checks are deterministic Python code; the LLM planner
only chooses which tool to call and supplies arguments.
"""
from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass
from typing import Any, Callable, Protocol
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# 1. Local project data: this is the source of truth, not the language model.
# ---------------------------------------------------------------------------
MODEL = {
    "elements": {
        "ElevatorController": {
            "type": "part",
            "package": "ElevatorStructure",
            "description": "Controls elevator behavior.",
        },
        "SoundSubsystem": {
            "type": "part",
            "package": "ElevatorStructure",
            "description": "Provides audio playback in the elevator car.",
        },
        "MovingUp": {
            "type": "state",
            "package": "ElevatorBehavior",
            "description": "Elevator is moving upward.",
        },
        "MovingDown": {
            "type": "state",
            "package": "ElevatorBehavior",
            "description": "Elevator is moving downward.",
        },
        "Idle": {
            "type": "state",
            "package": "ElevatorBehavior",
            "description": "Elevator is not moving.",
        },
    },
    "requirements": {
        "FR-15": {
            "title": "Audio playback",
            "text": "The elevator shall provide audio playback while the car is moving.",
        },
        "SR-03": {
            "title": "Safe operation",
            "text": "The elevator shall not perform unsupported operations.",
        },
    },
}

# Only these operation types can be proposed. A proposal is NOT applied to a model.
ALLOWED_OPERATIONS = {"add_part", "connect_part", "add_state_constraint"}


# ---------------------------------------------------------------------------
# 2. Typed tool definitions and deterministic implementations.
# ---------------------------------------------------------------------------
@dataclass
class Tool:
    name: str
    description: str
    parameters: dict[str, Any]
    handler: Callable[[dict[str, Any]], dict[str, Any]]


def require_exact_keys(args: dict[str, Any], required: set[str]) -> None:
    """Reject missing and unexpected keys, rather than silently ignoring them."""
    if not isinstance(args, dict):
        raise ValueError("Arguments must be a JSON object.")
    missing = required - set(args)
    extra = set(args) - required
    if missing:
        raise ValueError(f"Missing argument(s): {', '.join(sorted(missing))}")
    if extra:
        raise ValueError(f"Unexpected argument(s): {', '.join(sorted(extra))}")


def list_available_items(args: dict[str, Any]) -> dict[str, Any]:
    require_exact_keys(args, {"category"})
    category = args["category"]
    if category not in {"elements", "requirements"}:
        raise ValueError("category must be 'elements' or 'requirements'.")
    return {"category": category, "items": sorted(MODEL[category].keys())}


def get_metadata(args: dict[str, Any]) -> dict[str, Any]:
    require_exact_keys(args, {"item_id"})
    item_id = args["item_id"]
    if not isinstance(item_id, str) or not item_id.strip():
        raise ValueError("item_id must be a non-empty string.")
    for category in ("elements", "requirements"):
        if item_id in MODEL[category]:
            return {
                "item_id": item_id,
                "category": category,
                "metadata": MODEL[category][item_id],
            }
    return {"item_id": item_id, "found": False, "metadata": None}


def propose_typed_operation(args: dict[str, Any]) -> dict[str, Any]:
    require_exact_keys(args, {"operation", "target", "condition"})
    operation, target, condition = args["operation"], args["target"], args["condition"]
    if operation not in ALLOWED_OPERATIONS:
        raise ValueError(f"Unsupported operation. Allowed: {sorted(ALLOWED_OPERATIONS)}")
    if not all(isinstance(x, str) and x.strip() for x in (target, condition)):
        raise ValueError("target and condition must be non-empty strings.")
    # Return a candidate only. This function never edits MODEL or a SysML file.
    return {
        "status": "candidate_created",
        "candidate": {
            "operation": operation,
            "target": target,
            "condition": condition,
        },
    }


TOOLS = {
    "list_available_items": Tool(
        name="list_available_items",
        description="List IDs of available model elements or requirements.",
        parameters={"category": "string: elements | requirements"},
        handler=list_available_items,
    ),
    "get_metadata": Tool(
        name="get_metadata",
        description="Get metadata for one exact element or requirement ID.",
        parameters={"item_id": "string: exact model ID"},
        handler=get_metadata,
    ),
    "propose_typed_operation": Tool(
        name="propose_typed_operation",
        description="Create a typed engineering-operation proposal; does not apply it.",
        parameters={"operation": "string", "target": "string", "condition": "string"},
        handler=propose_typed_operation,
    ),
}


# ---------------------------------------------------------------------------
# 3. Independent engineering validation: the proposal is checked, not trusted.
# ---------------------------------------------------------------------------
def validate_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    """A tiny stand-in for a SysML compiler/official validator."""
    if set(candidate) != {"operation", "target", "condition"}:
        return {"valid": False, "reason": "Candidate has an invalid shape."}
    op, target, condition = candidate["operation"], candidate["target"], candidate["condition"]
    if op not in ALLOWED_OPERATIONS:
        return {"valid": False, "reason": "Operation is not in the allowlist."}
    if op == "add_part" and target not in {"SoundSubsystem", "ElevatorController"}:
        return {"valid": False, "reason": "Part target is not an approved project element."}
    if op == "add_state_constraint" and target not in {"SoundSubsystem"}:
        return {"valid": False, "reason": "State constraint target must be SoundSubsystem."}
    if op == "add_state_constraint" and condition != "active_only_in:MovingUp,MovingDown":
        return {"valid": False, "reason": "Unsupported state condition; expected MovingUp and MovingDown only."}
    if op == "connect_part" and target not in MODEL["elements"]:
        return {"valid": False, "reason": "Connection target does not exist in the local model."}
    return {"valid": True, "reason": "Candidate passed the local deterministic checks.", "applied": False}


# ---------------------------------------------------------------------------
# 4. Real LLM Planner using NVIDIA NIM (OpenAI-compatible API).
# ---------------------------------------------------------------------------
class Planner(Protocol):
    def decide(self, user_request: str, observations: list[dict[str, Any]]) -> dict[str, Any]: ...


class NvidiaPlanner:
    """Real model planner using NVIDIA NIM tool calling."""

    def __init__(self, model: str, api_key: str):
        from openai import OpenAI

        self.model = model
        self.client = OpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=api_key,
        )
        self.token_log: list[dict[str, int]] = []

    def decide(self, user_request: str, observations: list[dict[str, Any]]) -> dict[str, Any]:
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a cautious SysML assistant. Use only the supplied tools. "
                    "Do not invent model facts. If evidence is missing, say so. "
                    "Proposals are candidates only and are never applied automatically. "
                    "Once you have gathered enough observations or validated a proposal, "
                    "stop calling tools and provide a clear final answer."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Request: {user_request}\n"
                    f"Observed tool results so far: {json.dumps(observations)}"
                ),
            },
        ]

        tool_specs = []
        for tool in TOOLS.values():
            properties: dict[str, Any] = {}
            for key, description in tool.parameters.items():
                prop: dict[str, Any] = {"type": "string", "description": description}
                if key == "category":
                    prop["enum"] = ["elements", "requirements"]
                elif key == "operation":
                    prop["enum"] = sorted(ALLOWED_OPERATIONS)
                properties[key] = prop

            tool_specs.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": {
                        "type": "object",
                        "properties": properties,
                        "required": list(properties),
                        "additionalProperties": False,
                    },
                },
            })

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=tool_specs,
            tool_choice="auto",
            temperature=0.0,
            max_tokens=1024,
            stream=False,
        )

        if response.usage:
            self.token_log.append({
                "call": len(self.token_log) + 1,
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            })

        message = response.choices[0].message
        if message.tool_calls:
            call = message.tool_calls[0]
            raw_args = call.function.arguments
            if isinstance(raw_args, dict):
                parsed_args = raw_args
            else:
                try:
                    parsed_args = json.loads(raw_args)
                except (TypeError, json.JSONDecodeError):
                    parsed_args = raw_args
            return {
                "type": "tool_call",
                "name": call.function.name,
                "arguments": parsed_args,
            }

        return {"type": "final", "answer": message.content or "No answer was returned."}


# ---------------------------------------------------------------------------
# 5. Bounded control loop: decide -> validate -> execute -> observe -> repeat.
# ---------------------------------------------------------------------------
class SafeAgent:
    def __init__(self, planner: Planner, max_calls: int = 6, max_seconds: float = 45.0):
        self.planner = planner
        self.max_calls = max_calls
        self.max_seconds = max_seconds

    def run(self, user_request: str) -> dict[str, Any]:
        start = time.monotonic()
        observations: list[dict[str, Any]] = []
        call_count = 0

        while True:
            if time.monotonic() - start > self.max_seconds:
                return {"status": "stopped", "reason": "Time budget exceeded.", "observations": observations}

            decision = self.planner.decide(user_request, observations)
            if not isinstance(decision, dict):
                return {"status": "rejected", "reason": "Planner response must be an object.", "observations": observations}

            if decision.get("type") == "final":
                answer = decision.get("answer")
                if not isinstance(answer, str) or not answer.strip():
                    answer = "No verified answer is available."

                answer_lower = answer.lower()

                # 1. Entity-level grounding over successful tool observations
                validation_passed = any(
                    obs.get("validation", {}).get("valid") is True for obs in observations
                )
                any_tool_succeeded = any(obs.get("ok") is True for obs in observations)

                grounded_ids: set[str] = set()
                not_found_ids: set[str] = set()
                rejected_candidate_ids: set[str] = set()

                for obs in observations:
                    if obs.get("ok") is not True:
                        continue
                    res = obs.get("result", {})
                    tool_name = obs.get("tool")

                    if tool_name == "list_available_items":
                        grounded_ids.update(res.get("items", []))
                    elif tool_name == "get_metadata":
                        item_id = res.get("item_id", "")
                        if res.get("found") is False:
                            not_found_ids.add(item_id)
                        elif item_id:
                            grounded_ids.add(item_id)
                            meta = res.get("metadata") or {}
                            if isinstance(meta, dict) and "package" in meta:
                                grounded_ids.add(meta["package"])
                    elif tool_name == "propose_typed_operation":
                        cand = res.get("candidate", {})
                        if obs.get("validation", {}).get("valid") is True:
                            grounded_ids.add(cand.get("target", ""))
                            cond = cand.get("condition", "")
                            if ":" in cond:
                                grounded_ids.update(cond.split(":", 1)[1].split(","))
                        else:
                            rejected_candidate_ids.add(cand.get("target", ""))

                # 2. Extract model identifiers (CamelCase or REQ-XX) mentioned in final answer
                mentioned_ids = set(
                    re.findall(r"\b(?:[A-Z][a-z0-9]+){2,}\b|\b[A-Z]{2,}-\d+\b", answer)
                )
                unverified_mentions = mentioned_ids - grounded_ids - not_found_ids - rejected_candidate_ids

                # 3. Check if missing items were falsely claimed as existing
                has_negation = any(
                    phrase in answer_lower
                    for phrase in ("not found", "does not exist", "doesn't exist", "not in the", "missing")
                )

                claims_applied = any(
                    phrase in answer_lower
                    for phrase in (
                        "successfully added",
                        "has been added",
                        "implemented",
                        "applied to the model",
                        "updated the model",
                        "changed the model",
                    )
                )
                claims_validation = "validated" in answer_lower

                if claims_applied or (claims_validation and not validation_passed):
                    answer = (
                        "I cannot report an engineering change as successful. "
                        "The tools only inspect data or create a candidate; no model edit was applied."
                    )
                elif not any_tool_succeeded:
                    answer = "I cannot verify that claim because no valid tool evidence was collected."
                elif unverified_mentions:
                    unknown_list = ", ".join(sorted(unverified_mentions))
                    answer = (
                        f"I cannot verify claims about ungrounded model identifier(s): {unknown_list}. "
                        "No tool evidence was retrieved for them."
                    )
                elif not_found_ids and not has_negation:
                    missing_list = ", ".join(sorted(not_found_ids))
                    answer = f"The requested item(s) ({missing_list}) were not found in the local model."

                return {"status": "completed", "answer": answer, "observations": observations}

            if decision.get("type") != "tool_call":
                return {"status": "rejected", "reason": "Unknown decision type.", "observations": observations}

            if call_count >= self.max_calls:
                return {"status": "stopped", "reason": "Tool-call limit reached.", "observations": observations}

            name = decision.get("name")
            args = decision.get("arguments")
            call_count += 1

            if not isinstance(name, str) or name not in TOOLS:
                observations.append({"ok": False, "error": "Rejected unknown tool name."})
                continue

            try:
                result = TOOLS[name].handler(args)
                observation: dict[str, Any] = {"ok": True, "tool": name, "result": result}
                if name == "propose_typed_operation":
                    candidate = result["candidate"]
                    observation["validation"] = validate_candidate(candidate)
                observations.append(observation)
            except Exception as exc:
                observations.append({"ok": False, "tool": name, "error": str(exc)})


# ---------------------------------------------------------------------------
# 6. Run interactive agent with NVIDIA NIM & display token usage.
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    load_dotenv()

    nvidia_key = os.getenv("NVIDIA_API_KEY")
    if not nvidia_key:
        raise RuntimeError("NVIDIA_API_KEY is missing in .env file.")

    nvidia_model = os.getenv("NVIDIA_MODEL", "nvidia/nemotron-3.5-super-vl-120b-a12b")
    planner = NvidiaPlanner(model=nvidia_model, api_key=nvidia_key)
    agent = SafeAgent(planner, max_calls=12)

    prompt = input("What should I inspect or propose in the elevator model? ")
    result = agent.run(prompt)

    print("\n--- Final Natural Language Answer ---")
    print(result.get("answer") or f"Stopped early: {result.get('reason')}")

    print("\n--- Full Debug JSON ---")
    print(json.dumps(result, indent=2))

    print("\n--- Token Usage ---")
    print(json.dumps(planner.token_log, indent=2))
    print("Total Tokens:", sum(item["total_tokens"] for item in planner.token_log))