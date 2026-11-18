import time
from openai import OpenAI, APIStatusError, APIConnectionError

from src.config import API_KEY, MODEL_ID, BASE_URL
from src.prompts import build_messages


client = OpenAI(
    base_url=BASE_URL,
    api_key=API_KEY,
    timeout=60.0
)


def generate_response(project_request):

    messages = build_messages(project_request)

    start_time = time.perf_counter()

    try:
        completion = client.chat.completions.create(
            model=MODEL_ID,
            messages=messages,
            max_tokens=500,
            stream=False,
            extra_body={
                "chat_template_kwargs": {
                    "enable_thinking": False
                }
            }
        )

        duration = time.perf_counter() - start_time

        response_text = completion.choices[0].message.content

        usage = completion.usage

        return {
            "response": response_text,
            "model_id": MODEL_ID,
            "duration_seconds": round(duration, 3),
            "usage": usage.model_dump() if usage else None
        }

    except APIConnectionError as e:
        raise RuntimeError(f"Connection error: {e}") from e

    except APIStatusError as e:
        raise RuntimeError(
            f"Provider error {e.status_code}: {e.response.text}"
        ) from e