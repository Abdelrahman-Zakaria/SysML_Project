
"""
Main service that connects the prompt builder,
LLM client, and Intent validation.
"""

from models import Intent
from prompts import build_messages
from llm_client import generate_response
from response_handler import parse_and_validate


def generate_intent(user_request: str) -> tuple[Intent, object]:
    """
    Generate an Intent from a user request
    and validate the LLM response.
    """

    # Step 1: Prepare the chat messages.
    messages = build_messages(user_request)

    # Step 2: Send messages to the LLM.
    response = generate_response(messages)

    # Step 3: Check that the response contains a choice.
    if not response.choices:
        raise ValueError("The LLM returned no response choices.")

    # Step 4: Extract the assistant's response text.
    raw_content = response.choices[0].message.content

    if not isinstance(raw_content, str) or not raw_content.strip():
        raise ValueError("The LLM returned empty content.")

    # Step 5: Parse JSON and validate it with Pydantic.
    intent = parse_and_validate(raw_content)

    # Return both the validated Intent and full response.
    return intent, response
