
import httpx

from google.genai.errors import APIError
from pydantic import ValidationError

from prompts import build_intent_prompt, PROMPT_VERSION
from llm_client import generate_text
from schemas import SystemIntent
from semantic_validation import (
    validate_semantics,
    SemanticValidationError
)
from response_parser import (
    parse_json_response,
    InvalidJSONResponse
)


def display_execution_info(result):
    print("\n--- Execution Information ---")
    print(f"Provider: {result.provider}")
    print(f"Model ID: {result.model_id}")
    print(f"Prompt Version: {result.prompt_version}")
    print(f"Response Time: {result.duration_seconds:.2f} seconds")

    print(f"Input Tokens: {result.input_tokens}")
    print(f"Output Tokens: {result.output_tokens}")
    print(f"Total Tokens: {result.total_tokens}")

    if result.estimated_cost_usd is not None:
        print(f"Estimated API Cost: ${result.estimated_cost_usd:.8f}")

        if result.estimated_cost_usd == 0:
            print("Pricing Tier: Free Tier")
    else:
        print("Estimated API Cost: Not calculated")


def main():
    # Synthetic engineering request
    user_description = """
    Design an electric vehicle charging system
    that supports 10 vehicles simultaneously.
    It should include an emergency shutdown mechanism
    and a power monitoring unit.
    """

    prompt = build_intent_prompt(user_description)

    try:
        # Step 1: Generate structured intent using Gemini
        result = generate_text(prompt, PROMPT_VERSION)

        display_execution_info(result)

        print("\n--- Raw Gemini Response ---")
        print(result.text)

        # Step 2: JSON Parsing
        try:
            data = parse_json_response(result.text)

        except InvalidJSONResponse as e:
            print("\nJSON Parsing Failed:")
            print(e)
            return

        # Step 3: Schema Validation
        try:
            intent = SystemIntent.model_validate(data)

        except ValidationError as e:
            print("\nSchema Validation Failed:")
            print(e)
            return

        # Step 4: Semantic Validation
        try:
            validate_semantics(intent)

        except SemanticValidationError as e:
            print("\nSemantic Validation Failed:")
            print(e)
            return

        # Step 5: Display validated result
        print("\n--- All Validations Successful! ---")
        print(intent.model_dump_json(indent=2))

    except APIError as e:

        error_message = str(e).lower()

        if e.code == 429 and (
            "per day limit exceeded" in error_message
            or "generaterequestsperday" in error_message
        ):
            print("\nGemini Daily Free Tier Quota Exceeded.")
            print("You have reached the daily request limit.")
            print("Please try again after the quota resets.")
            print("Check your usage at:")
            print("https://ai.dev/rate-limit")

        else:
            print("\nGemini API Error:")
            print(e)

    except (httpx.TimeoutException, TimeoutError) as e:
        print("\nRequest Timeout:")
        print(e)

    except RuntimeError as e:
        print("\nApplication Error:")
        print(e)

    except Exception as e:
        print("\nUnexpected Error:")
        print(e)


if __name__ == "__main__":
    main()
