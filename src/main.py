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

    api_requests = 0
    input_tokens = 0
    output_tokens = 0
    total_tokens = 0

    def display_usage():
        print("\n========== TOKEN USAGE ==========")
        print(f"API Requests:  {api_requests}")
        print(f"Input Tokens:  {input_tokens}")
        print(f"Output Tokens: {output_tokens}")
        print(f"Total Tokens:  {total_tokens}")
        print("=================================")

    while tool_call_count < max_tool_calls:

        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto"
        )

        api_requests += 1

        if getattr(response, "usage", None):
            input_tokens += response.usage.prompt_tokens
            output_tokens += response.usage.completion_tokens
            total_tokens += response.usage.total_tokens

        assistant_message = response.choices[0].message

        messages.append(
            assistant_message.model_dump(exclude_none=True)
        )

        if not assistant_message.tool_calls:
            display_usage()
            return assistant_message.content

        for tool_call in assistant_message.tool_calls:

            if tool_call_count >= max_tool_calls:
                display_usage()
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

    display_usage()
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