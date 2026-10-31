import os
import json
import time
from typing import Literal

from dotenv import load_dotenv
from huggingface_hub import InferenceClient
from huggingface_hub.errors import (
    HfHubHTTPError,
    InferenceEndpointTimeoutError,
    InferenceTimeoutError,
)
from pydantic import BaseModel, Field, ValidationError

load_dotenv()

PROMPT_VERSION = "v1.1"
MAX_PROMPT_LENGTH = 2_000

# 1. Output Contract
class SystemModelingIntent(BaseModel):
    action: Literal["generate", "validate", "extract"]
    target_component: str = Field(min_length=1)
    confidence_score: float = Field(ge=0.0, le=1.0)

def clean_json_payload(raw_text: str) -> str:
    decoder = json.JSONDecoder()
    for index, character in enumerate(raw_text):
        if character != "{":
            continue
        try:
            _, end = decoder.raw_decode(raw_text[index:])
        except json.JSONDecodeError:
            continue
        return raw_text[index:index + end]
    return raw_text.strip()

def get_required_setting(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value

def get_model_intent(user_prompt: str) -> SystemModelingIntent | None:
    try:
        if not user_prompt.strip():
            raise ValueError("The user prompt cannot be empty.")
        if len(user_prompt) > MAX_PROMPT_LENGTH:
            raise ValueError(f"The user prompt cannot exceed {MAX_PROMPT_LENGTH} characters.")

        # 2. Setup Hugging Face Client pointing to Google Gemini
        base_url = get_required_setting("BASE_URL")
        api_key = get_required_setting("GEMINI_API_KEY")
        model_id = get_required_setting("MODEL_ID")
        
        client = InferenceClient(
            base_url=base_url,
            api_key=api_key,
        )

        schema_json = json.dumps(SystemModelingIntent.model_json_schema())
        system_prompt = f"""
You classify SysML v2 engineering requests.

Choose exactly one action:
- generate: the user wants to create something
- validate: the user wants to check something
- extract: the user wants to retrieve information

Identify the target component or concept in the user's request.
Return only valid JSON matching this schema:
{schema_json}
Example Output: {{"action": "generate", "target_component": "thermal model", "confidence_score": 0.95}}
"""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        # 3. Track Duration
        start_time = time.perf_counter()
        response = client.chat_completion(
            model=model_id,
            messages=messages,
            max_tokens=500,
            temperature=0.1
        )
        duration = time.perf_counter() - start_time

        if not response.choices:
            raise ValueError("The API returned no choices.")
        raw_content = response.choices[0].message.content
        if not isinstance(raw_content, str) or not raw_content.strip():
            raise ValueError("The model returned an empty response.")

        print(f"Prompt Version: {PROMPT_VERSION}")
        print(f"Model ID: {model_id}")
        print(f"Duration: {duration:.2f} seconds")
        
        # 4. Token Tracking (Lab Requirement)
        if hasattr(response, 'usage') and response.usage:
            print(f"Tokens Used: Prompt={response.usage.prompt_tokens}, Completion={response.usage.completion_tokens}")

        cleaned_json = clean_json_payload(raw_content)

        # 5. Pydantic Validation
        return SystemModelingIntent.model_validate_json(cleaned_json)

    # 6. Error Handling
    except (InferenceTimeoutError, InferenceEndpointTimeoutError, TimeoutError):
        print("Error: The API request timed out.")
    except ValidationError as e:
        print(f"Error: The model returned invalid JSON structure.\n{e}")
    except (HfHubHTTPError, ValueError) as e:
        print(f"Error: {e}")
    except (AttributeError, IndexError, TypeError) as e:
        print(f"Error: The API returned an unexpected response format: {e}")

    return None


if __name__ == "__main__":
    print("=== SysML v2 Intent Extraction ===")
    print("Type a natural language system modeling request.")
    print("(e.g., 'Check the engine mass', 'Build a thermal model', 'Find constraints')\n")
    
    try:
        user_input = ""
        while not user_input:
            user_input = input("Your request: ").strip()
            if not user_input:
                print("Input cannot be empty. Please enter a system modeling request.")
            elif len(user_input) > MAX_PROMPT_LENGTH:
                print(f"Input cannot exceed {MAX_PROMPT_LENGTH} characters. Please shorten your request.")
                user_input = ""
    except (KeyboardInterrupt, EOFError):
        print("\nInput cancelled. Goodbye.")
        raise SystemExit(0)

    print("\nAnalyzing intent...\n")

    intent = get_model_intent(user_input)
    if intent:
        print("\n--- VALIDATION SUCCESS ---")
        print("Validated Pydantic Object:")
        print(f"Action: {intent.action}")
        print(f"Target: {intent.target_component}")
        print(f"Confidence: {intent.confidence_score}")