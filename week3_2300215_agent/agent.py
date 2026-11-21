import json
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from huggingface_hub import InferenceClient
from huggingface_hub.errors import (
    HfHubHTTPError,
    InferenceEndpointTimeoutError,
    InferenceTimeoutError,
)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from week3_2300215_agent.tools import dispatch_tool

load_dotenv()

MAX_PROMPT_LENGTH = 2_000


def get_required_setting(name: str) -> str:
    """Fetches a required environment variable or raises ValueError."""
    value = os.getenv(name)
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


# Tool schemas exposed to the LLM
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "list_elements",
            "description": "List all valid element IDs in the SysML model.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_element_details",
            "description": "Get details for a single SysML element by exact ID (e.g., REQ-101 or BLK-204).",
            "parameters": {
                "type": "object",
                "properties": {
                    "element_id": {
                        "type": "string",
                        "description": "Exact SysML ID formatted as REQ-XXX or BLK-XXX.",
                    }
                },
                "required": ["element_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "validate_operation",
            "description": "Check whether a proposed mass in kg for a block satisfies requirement REQ-101.",
            "parameters": {
                "type": "object",
                "properties": {
                    "target_id": {
                        "type": "string",
                        "description": "Block ID formatted as BLK-XXX.",
                    },
                    "proposed_mass_kg": {
                        "type": "number",
                        "description": "Proposed mass in kilograms (must be greater than 0).",
                    },
                },
                "required": ["target_id", "proposed_mass_kg"],
            },
        },
    },
]


def run_agent(
    user_prompt: str,
    ask_llm,
    max_calls: int = 5,
    max_seconds: float = 20.0,
    max_total_tokens: int = 6_000,
) -> dict:
    """Executes the bounded tool-calling control loop."""
    if not user_prompt or not user_prompt.strip():
        return {"status": "error", "reason": "EMPTY_PROMPT", "messages": []}
    if len(user_prompt) > MAX_PROMPT_LENGTH:
        return {"status": "error", "reason": "PROMPT_TOO_LONG", "messages": []}

    messages = [
        {
            "role": "system",
            "content": (
                "You are a SysML v2 engineering assistant. Always use your tools to inspect facts. "
                "If an element is missing or a tool returns an error, state that clearly—never guess."
            ),
        },
        {"role": "user", "content": user_prompt},
    ]

    start_time = time.perf_counter()
    calls_used = 0
    tokens_used = 0
    seen_calls = set()

    for _ in range(max_calls):
        if (time.perf_counter() - start_time) > max_seconds:
            return {
                "status": "stopped",
                "reason": "TIMEOUT_EXCEEDED",
                "calls_used": calls_used,
                "tokens_used": tokens_used,
                "messages": messages,
            }

        reply = ask_llm(messages)

        if reply.get("error"):
            return {
                "status": "error",
                "reason": reply["error"],
                "calls_used": calls_used,
                "tokens_used": tokens_used,
                "messages": messages,
            }

        tokens_used += reply.get("tokens", 0)
        if tokens_used > max_total_tokens:
            return {
                "status": "stopped",
                "reason": "TOKEN_BUDGET_EXCEEDED",
                "calls_used": calls_used,
                "tokens_used": tokens_used,
                "messages": messages,
            }

        tool_calls = reply.get("tool_calls") or []

        # Final text answer returned when no tools are requested
        if not tool_calls:
            final_text = reply.get("content", "")
            messages.append({"role": "assistant", "content": final_text})
            return {
                "status": "completed",
                "answer": final_text,
                "calls_used": calls_used,
                "tokens_used": tokens_used,
                "duration_sec": round(time.perf_counter() - start_time, 2),
                "messages": messages,
            }

        # Record assistant tool proposals, preserving Gemini 3.x thought signatures
        assistant_tool_calls = []
        for i, tc in enumerate(tool_calls, start=1):
            formatted_tc = {
                "id": tc.get("id") or f"call_{i}",
                "type": "function",
                "function": {
                    "name": tc["name"],
                    "arguments": json.dumps(tc.get("args", {})),
                },
            }
            if "extra_content" in tc:
                formatted_tc["extra_content"] = tc["extra_content"]
            assistant_tool_calls.append(formatted_tc)

        messages.append({
            "role": "assistant",
            "content": reply.get("content") or None,
            "tool_calls": assistant_tool_calls,
        })

        # Validate and dispatch each tool call
        for tc in tool_calls:
            if calls_used >= max_calls:
                return {
                    "status": "stopped",
                    "reason": "MAX_CALLS_REACHED",
                    "calls_used": calls_used,
                    "tokens_used": tokens_used,
                    "messages": messages,
                }

            name = tc["name"]
            args = tc.get("args", {})
            call_id = tc.get("id") or f"call_{calls_used + 1}"
            call_key = (name, json.dumps(args, sort_keys=True))

            # Prevent infinite loops on identical repeated calls
            if call_key in seen_calls:
                return {
                    "status": "stopped",
                    "reason": "REPEATED_CALL",
                    "calls_used": calls_used,
                    "tokens_used": tokens_used,
                    "messages": messages,
                }

            seen_calls.add(call_key)
            calls_used += 1

            observation = dispatch_tool(name, args)

            messages.append({
                "role": "tool",
                "tool_call_id": call_id,
                "name": name,
                "content": json.dumps(observation),
            })

    return {
        "status": "stopped",
        "reason": "MAX_CALLS_REACHED",
        "calls_used": calls_used,
        "tokens_used": tokens_used,
        "messages": messages,
    }


def make_gemini_llm():
    """Creates an OpenAI-compatible InferenceClient wrapper for Gemini."""
    base_url = get_required_setting("BASE_URL")
    api_key = get_required_setting("GEMINI_API_KEY")
    model_id = get_required_setting("MODEL_ID")

    client = InferenceClient(
        base_url=base_url,
        api_key=api_key,
    )

    def ask_gemini(messages: list) -> dict:
        try:
            response = client.chat_completion(
                model=model_id,
                messages=messages,
                tools=TOOL_SCHEMAS,
                tool_choice="auto",
                max_tokens=1024,
            )
        except (InferenceTimeoutError, InferenceEndpointTimeoutError, TimeoutError):
            return {"error": "API_TIMEOUT"}
        except HfHubHTTPError as e:
            return {"error": f"API_HTTP_ERROR: {e}"}
        except Exception as e:
            return {"error": f"API_UNEXPECTED_ERROR: {e}"}

        if not response.choices:
            return {"error": "API_EMPTY_CHOICES"}

        msg = response.choices[0].message

        turn_tokens = 0
        if getattr(response, "usage", None):
            turn_tokens = (response.usage.prompt_tokens or 0) + (response.usage.completion_tokens or 0)

        parsed_calls = []
        if msg.tool_calls:
            for idx, tc in enumerate(msg.tool_calls, start=1):
                try:
                    args = json.loads(tc.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {"__invalid_json__": tc.function.arguments}

                call_entry = {
                    "id": tc.id or f"call_{idx}",
                    "name": tc.function.name,
                    "args": args,
                }
                extra_content = getattr(tc, "extra_content", None)
                if extra_content is not None:
                    call_entry["extra_content"] = extra_content

                parsed_calls.append(call_entry)

        return {
            "content": msg.content or "",
            "tool_calls": parsed_calls,
            "tokens": turn_tokens,
        }

    return ask_gemini


if __name__ == "__main__":
    print("=== Week 3: Safe SysML Tool-Calling Agent ===")
    print("Examples:")
    print("  - List all elements and check if BLK-204 can weigh 48 kg.")
    print("  - Inspect element REQ-999.\n")

    try:
        user_input = input("Your request: ").strip()
    except (KeyboardInterrupt, EOFError):
        print("\nCancelled.")
        raise SystemExit(0)

    if not user_input:
        print("Empty prompt—exiting.")
        raise SystemExit(0)

    gemini_llm = make_gemini_llm()
    outcome = run_agent(user_input, ask_llm=gemini_llm)

    print("\n--- RESULT ---")
    print("Status:", outcome["status"])
    if outcome.get("reason"):
        print("Reason:", outcome["reason"])
    print("Tool Calls Used:", outcome.get("calls_used", 0))
    print("Tokens Used:", outcome.get("tokens_used", 0))
    if outcome.get("duration_sec") is not None:
        print(f"Duration: {outcome['duration_sec']}s")
    if outcome.get("answer"):
        print("\nAgent Answer:\n" + outcome["answer"])