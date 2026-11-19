
import pytest

from prompts import SYSTEM_PROMPT, build_messages


# Test 1: The builder creates the correct message roles.
def test_build_messages_returns_correct_roles():
    messages = build_messages("Draft a functional requirement.")

    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    assert len(messages) == 2


# Test 2: The system message contains our instructions.
def test_system_message_contains_prompt():
    messages = build_messages("Draft a functional requirement.")

    assert messages[0]["content"] == SYSTEM_PROMPT


# Test 3: The user request is included correctly.
def test_user_message_contains_request():
    request = "Draft a functional elevator requirement."

    messages = build_messages(request)

    assert messages[1]["content"] == request


# Test 4: Empty requests must be rejected.
def test_empty_request_is_rejected():
    with pytest.raises(ValueError):
        build_messages("")


# Test 5: Whitespace-only requests must be rejected.
def test_whitespace_request_is_rejected():
    with pytest.raises(ValueError):
        build_messages("   ")


# Test 6: Non-string inputs must be rejected.
def test_non_string_request_is_rejected():
    with pytest.raises(ValueError):
        build_messages(123)
