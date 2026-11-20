
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
    print("Model:", MODEL_ID)
    print("Provider:", INFERENCE_PROVIDER)
    print("Prompt version:", PROMPT_VERSION)

    intent, response = generate_intent(user_request)

    print("\nValidated Intent:")
    print(intent.model_dump_json(indent=4))

    usage = response.usage

    if usage:
        print("\nToken Usage:")
        print("Input:", usage.prompt_tokens)
        print("Output:", usage.completion_tokens)
        print("Total:", usage.total_tokens)
    else:
        print("\nToken usage was not provided.")


if __name__ == "__main__":
    main()
