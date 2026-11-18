import json
import os
from datetime import datetime, timezone

from src.inference import generate_response
from src.validator import validate_response
from src.prompts import PROMPT_VERSION


PROJECT_REQUEST = """
Build a Smart Parking System using ultrasonic sensors
and an embedded controller.

The system should detect available parking spaces
and allow users to monitor availability through
a mobile application.
"""


def save_execution_log(metadata):

    os.makedirs("logs", exist_ok=True)

    with open("logs/execution_log.jsonl", "a") as file:
        file.write(json.dumps(metadata) + "\n")


def main():

    metadata = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "provider": "NVIDIA",
        "prompt_version": PROMPT_VERSION,
        "status": "failed"
    }

    try:
        result = generate_response(PROJECT_REQUEST)

        metadata.update({
            "model_id": result["model_id"],
            "duration_seconds": result["duration_seconds"]
        })

        usage = result["usage"]

        if usage:
            metadata.update({
                "input_tokens": usage.get("prompt_tokens"),
                "output_tokens": usage.get("completion_tokens"),
                "total_tokens": usage.get("total_tokens")
            })

        intent = validate_response(result["response"])

        metadata["status"] = "success"

        print("\nValidated Project Intent:")
        print(intent.model_dump_json(indent=4))

    except (RuntimeError, ValueError) as e:
        metadata["status"] = "failed"
        print(f"\nError: {e}")

    finally:
        save_execution_log(metadata)

        print("\nExecution Metadata:")
        print(json.dumps(metadata, indent=4))


if __name__ == "__main__":
    main()