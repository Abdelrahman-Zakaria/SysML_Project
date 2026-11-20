import os
import json
from google import genai


class RuleBasedPlanner:
    """
    A simple rule-based planner.
    Selects tools using predefined keywords without an LLM.
    """

    def plan(self, user_request: str) -> dict:
        request = user_request.lower()

        # 1. List available Blocks or Requirements
        if "list" in request or "show all" in request:

            if "requirement" in request:
                return {
                    "calls": [
                        {
                            "tool_name": "list_available_items",
                            "arguments": {
                                "item_type": "Requirement"
                            }
                        }
                    ]
                }

            return {
                "calls": [
                    {
                        "tool_name": "list_available_items",
                        "arguments": {
                            "item_type": "Block"
                        }
                    }
                ]
            }

        # 2. Get element metadata
        if "metadata" in request or "details" in request:

            element_id = None

            for word in user_request.split():
                word = word.strip(".,?!")

                if word.upper().startswith(("REQ-", "BLK-")):
                    element_id = word
                    break

            if element_id:
                return {
                    "calls": [
                        {
                            "tool_name": "get_metadata",
                            "arguments": {
                                "element_id": element_id
                            }
                        }
                    ]
                }

        # 3. Check whether a Block has attributes
        if "attribute" in request:

            element_id = None

            for word in user_request.split():
                word = word.strip(".,?!")

                if word.upper().startswith("BLK-"):
                    element_id = word
                    break

            if element_id:
                return {
                    "calls": [
                        {
                            "tool_name": "check_condition",
                            "arguments": {
                                "element_id": element_id,
                                "condition": "has_attributes"
                            }
                        }
                    ]
                }

        # 4. Check whether an element exists
        if "exist" in request:

            element_id = None

            for word in user_request.split():
                word = word.strip(".,?!")

                if word.upper().startswith(("BLK-", "REQ-")):
                    element_id = word
                    break

            if element_id:
                return {
                    "calls": [
                        {
                            "tool_name": "check_condition",
                            "arguments": {
                                "element_id": element_id,
                                "condition": "exists"
                            }
                        }
                    ]
                }

        # No suitable tool found
        return {"calls": []}




class LLMPlanner:
    """
    Uses Gemini to understand user intent and select tools.
    Supports different phrasings and common spelling mistakes.
    """

    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise ValueError("GEMINI_API_KEY is missing")

        self.client = genai.Client(api_key=api_key)

        self.model = os.getenv(
            "GEMINI_MODEL",
            "gemini-2.5-flash"
        )

    def plan(self, user_request: str) -> dict:

        prompt = f"""
You are an intelligent tool planner for a SysML assistant.

Your job is to understand the INTENT and MEANING of the user's
request, then select the most appropriate available tool.

IMPORTANT UNDERSTANDING RULES:
- Do not depend on exact keywords.
- Understand natural language and different sentence structures.
- Tolerate common spelling mistakes and typos.
- Understand synonyms and equivalent expressions.
- Focus on what the user wants to achieve, not the exact words.
- Do not reject a request just because it contains spelling errors.

AVAILABLE TOOLS:

1. list_available_items
Purpose:
List elements stored in the model.

Required argument:
- item_type: "Block" or "Requirement"

Use this tool when the user wants to:
- See all requirements.
- Show system requirements.
- Get a list of requirements.
- Display requirements.
- Find out what requirements exist.
- See all blocks or system components.

2. get_metadata
Purpose:
Retrieve complete information about one specific element.

Required argument:
- element_id: string

Use this tool when the user asks for details,
description, or metadata about a specific element.

3. check_condition
Purpose:
Check a condition on a specific element.

Required arguments:
- element_id: string
- condition: "exists" or "has_attributes"

Use this tool when the user asks whether an element exists
or whether a Block has attributes.

EXAMPLES:

User: "Show all requriments"
Output:
{{
  "calls": [
    {{
      "tool_name": "list_available_items",
      "arguments": {{"item_type": "Requirement"}}
    }}
  ]
}}

User: "I want to see the system requirements"
Output:
{{
  "calls": [
    {{
      "tool_name": "list_available_items",
      "arguments": {{"item_type": "Requirement"}}
    }}
  ]
}}

User: "What components do we have?"
Output:
{{
  "calls": [
    {{
      "tool_name": "list_available_items",
      "arguments": {{"item_type": "Block"}}
    }}
  ]
}}

User: "Tell me about REQ-001"
Output:
{{
  "calls": [
    {{
      "tool_name": "get_metadata",
      "arguments": {{"element_id": "REQ-001"}}
    }}
  ]
}}

IMPORTANT SAFETY RULES:
- Use only the three available tools.
- Never invent tool names.
- Never invent element IDs.
- Never invent arguments or data.
- If the user's intent is unrelated to all available tools,
  return an empty calls list.
- If the intent is clear but a required element ID is missing,
  do not invent one. Return an empty calls list.
- Return valid JSON only. No Markdown or explanations.

EXPECTED JSON FORMAT:

{{
  "calls": [
    {{
      "tool_name": "tool_name",
      "arguments": {{}}
    }}
  ]
}}

If no tool is suitable, return:

{{
  "calls": []
}}

USER REQUEST:
{user_request}
"""

        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "temperature": 0
            }
        )

        if not response.text:
            raise ValueError("Gemini returned an empty response")

        result = json.loads(response.text)

        if not isinstance(result, dict):
            raise ValueError("Gemini returned an invalid plan")

        if not isinstance(result.get("calls"), list):
            raise ValueError("Gemini response must contain a calls list")

        return result