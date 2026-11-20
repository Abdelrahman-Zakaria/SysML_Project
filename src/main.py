import json
from openai import OpenAI

from src.config import API_KEY, MODEL, BASE_URL
from src.agent import execute_tool


client = OpenAI(
    api_key=API_KEY,
    base_url=BASE_URL,
    timeout=30.0
)


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_available_items",
            "description": "Lists all elements in the Elevator System.",
            "parameters": {
                "type": "object",
                "properties": {},
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_metadata",
            "description": "Retrieves metadata about an elevator element using its ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "item_id": {
                        "type": "integer",
                        "description": "The ID of the elevator element."
                    }
                },
                "required": ["item_id"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_condition",
            "description": "Checks whether an elevator element satisfies a specified condition.",
            "parameters": {
                "type": "object",
                "properties": {
                    "item_id": {
                        "type": "integer"
                    },
                    "condition": {
                        "type": "string",
                        "enum": ["exists", "available", "defined"]
                    }
                },
                "required": ["item_id", "condition"],
                "additionalProperties": False
            }
        }
    }
]


def run_agent(user_input):

    messages = [
        {
            "role": "system",
            "content": (
                "You are an assistant for inspecting an Elevator System. "
                "Use the available tools to retrieve information. "
                "Never invent tool results. "
                "If the tools do not provide enough information, say so. "
                "Distinguish between an element's actual status and "
                "whether a requested condition is satisfied."
            )
        },
        {
            "role": "user",
            "content": user_input
        }
    ]

    max_tool_calls = 5
    tool_call_count = 0

    while tool_call_count < max_tool_calls:

        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto"
        )

        assistant_message = response.choices[0].message

        messages.append(
            assistant_message.model_dump(exclude_none=True)
        )

        if not assistant_message.tool_calls:
            return assistant_message.content

        for tool_call in assistant_message.tool_calls:

            if tool_call_count >= max_tool_calls:
                return "Maximum tool-call limit reached."

            tool_call_count += 1

            tool_name = tool_call.function.name

            try:
                arguments = json.loads(
                    tool_call.function.arguments
                )

                if not isinstance(arguments, dict):
                    raise ValueError(
                        "Tool arguments must be a JSON object."
                    )

                result = execute_tool(tool_name, arguments)

            except (json.JSONDecodeError, ValueError) as error:
                result = {
                    "error": f"Invalid tool request: {error}"
                }

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result)
            })

    return "Maximum tool-call limit reached."


if __name__ == "__main__":

    while True:

        user_input = input("\nYou: ")

        if user_input.lower() in ["exit", "quit"]:
            break

        try:
            answer = run_agent(user_input)
            print("\nAgent:", answer)

        except Exception as error:
            print("\nError:", error)