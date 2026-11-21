
import json

from config import MODEL_ID, INFERENCE_PROVIDER
from prompts import PROMPT_VERSION
from intent_service import generate_intent


def main():
    user_request = (
        "Draft a functional requirement stating that "
        "the elevator shall stop at the floor selected "
        "by the passenger. Do not modify the model."
    )

    print("Generating intent...")

    intent, response, metadata = generate_intent(user_request)

    print("\nValidated Intent:")
    print(intent.model_dump_json(indent=4))

    print("\nRun Metadata:")
    print(json.dumps(metadata, indent=4))


if __name__ == "__main__":
    main()
