"""Offline tests for ChatSession (generate_intent is replaced by a fake)."""

import json

from chat import ChatSession, format_intent
from intent_service import LLMRequestError
from models import Intent


def make_intent(**overrides):
    data = {
        "schema_version": "1.0",
        "intent_type": "draft_requirement",
        "requirement_type": "functional",
        "requirement_text": "The elevator shall stop at the floor selected by the passenger.",
        "clarification_needed": False,
        "clarification_question": None,
    }
    data.update(overrides)
    return Intent.model_validate(data)


CLARIFY = dict(
    requirement_type="unspecified",
    requirement_text=None,
    clarification_needed=True,
    clarification_question="What should the brakes do?",
)
UNSUPPORTED = dict(
    intent_type="unsupported",
    requirement_type="unspecified",
    requirement_text=None,
)


class FakeGenerate:
    """Records calls and returns queued Intents (or raises queued errors)."""

    def __init__(self, *results):
        self.results = list(results)
        self.calls = []

    def __call__(self, text, history):
        self.calls.append((text, history))
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result, object(), {"total_tokens": 10}


def test_requirement_is_shown_readably_not_as_raw_json():
    session = ChatSession(generate=FakeGenerate(make_intent()))
    reply, done = session.handle_input("Draft an elevator requirement")

    assert not done
    assert "Intent: draft_requirement" in reply
    assert "Requirement type: functional" in reply
    assert "Requirement: The elevator shall stop" in reply
    assert "Clarification needed: No" in reply
    assert "{" not in reply


def test_clarification_reply_shows_question():
    session = ChatSession(generate=FakeGenerate(make_intent(**CLARIFY)))
    reply, _ = session.handle_input("Write a requirement for the brakes.")

    assert "Clarification needed: Yes" in reply
    assert "What should the brakes do?" in reply


def test_unsupported_request_is_explained():
    session = ChatSession(generate=FakeGenerate(make_intent(**UNSUPPORTED)))
    reply, _ = session.handle_input("Write Python code")

    assert "unsupported" in reply
    assert "outside" in reply


def test_repeated_messages_share_history():
    gen = FakeGenerate(make_intent(**CLARIFY), make_intent())
    session = ChatSession(generate=gen)

    session.handle_input("Write a requirement for the brakes.")
    session.handle_input("They must stop the car in 40 m.")

    assert gen.calls[0][1] == []
    second_history = gen.calls[1][1]
    assert [m["role"] for m in second_history] == ["user", "assistant"]
    assert second_history[0]["content"] == "Write a requirement for the brakes."
    # the assistant turn is the validated Intent JSON
    assert json.loads(second_history[1]["content"])["clarification_needed"] is True


def test_history_is_limited():
    gen = FakeGenerate(*[make_intent() for _ in range(6)])
    session = ChatSession(generate=gen, max_history_messages=4)

    for i in range(6):
        session.handle_input(f"request {i}")

    assert len(session.history) == 4
    assert session.history[0] == {"role": "user", "content": "request 4"}
    assert len(gen.calls[5][1]) == 4  # never more than the limit is sent


def test_clear_resets_history_and_json():
    session = ChatSession(generate=FakeGenerate(make_intent()))
    session.handle_input("Draft something")

    reply, done = session.handle_input("/clear")

    assert reply == "Conversation cleared."
    assert not done
    assert session.history == []
    assert "No Intent yet" in session.handle_input("/json")[0]


def test_json_command_shows_latest_intent():
    session = ChatSession(generate=FakeGenerate(make_intent()))
    assert "No Intent yet" in session.handle_input("/json")[0]

    session.handle_input("Draft something")
    reply, _ = session.handle_input("/json")

    assert json.loads(reply)["intent_type"] == "draft_requirement"


def test_help_and_exit_and_unknown_commands():
    session = ChatSession(generate=FakeGenerate())

    help_reply, done = session.handle_input("/help")
    assert not done
    for command in ("/help", "/clear", "/json", "/exit"):
        assert command in help_reply

    assert session.handle_input("/EXIT") == ("Goodbye!", True)
    reply, done = session.handle_input("/nonsense")
    assert "Unknown command" in reply and not done


def test_empty_input_is_handled_without_calling_the_model():
    gen = FakeGenerate()
    session = ChatSession(generate=gen)

    for text in ("", "   ", None):
        reply, done = session.handle_input(text)
        assert "Please type" in reply and not done

    assert gen.calls == []


def test_errors_do_not_crash_and_are_not_remembered():
    gen = FakeGenerate(
        LLMRequestError("The LLM request failed (X): boom"),
        ValueError("The LLM returned invalid JSON."),
        RuntimeError("something odd"),
        make_intent(),
    )
    session = ChatSession(generate=gen)

    assert "boom" in session.handle_input("one")[0]
    assert "invalid JSON" in session.handle_input("two")[0]
    assert "Unexpected error" in session.handle_input("three")[0]
    assert session.history == [] and session.last_intent is None

    assert "Requirement:" in session.handle_input("four")[0]  # still alive


def test_format_intent_unsupported():
    assert "unsupported" in format_intent(make_intent(**UNSUPPORTED))
