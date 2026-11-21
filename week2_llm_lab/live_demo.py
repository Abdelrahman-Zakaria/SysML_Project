import json
import sys

from intent_service import LLMRequestError, generate_intent


def main():
    """One-shot demo. For the interactive chatbot run: python main.py"""

    user_request = (
        " ".join(sys.argv[1:])
        or "Draft a functional requirement stating that "
        "the elevator shall stop at the floor selected "
        "by the passenger. Do not modify the model."
    )

    print("Generating intent...")

    try:
        intent, _response, metadata = generate_intent(user_request)
    except (LLMRequestError, ValueError, RuntimeError) as exc:
        print(f"Error: {exc}")
        return 1

    print("\nValidated Intent:")
    print(intent.model_dump_json(indent=4))

    print("\nRun Metadata:")
    print(json.dumps(metadata, indent=4))
    return 0


if __name__ == "__main__":
    sys.exit(main())
