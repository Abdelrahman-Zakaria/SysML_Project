"""Offline tests for the terminal loop in main.py."""

from chat import ChatSession
from main import run_chat
from test_chat import FakeGenerate, make_intent


def run(inputs, session):
    lines = iter(inputs)
    output = []
    run_chat(session, input_fn=lambda prompt: next(lines), print_fn=output.append)
    return "\n".join(output)


def test_multiple_messages_then_exit():
    session = ChatSession(generate=FakeGenerate(make_intent(), make_intent()))
    out = run(["first", "second", "/exit"], session)

    assert out.count("Requirement type: functional") == 2
    assert "Goodbye!" in out


def test_empty_input_does_not_end_the_loop():
    session = ChatSession(generate=FakeGenerate())
    out = run(["", "/exit"], session)

    assert "Please type a request" in out


def test_end_of_input_exits_cleanly():
    def raise_eof(prompt):
        raise EOFError

    out = []
    run_chat(ChatSession(generate=FakeGenerate()), input_fn=raise_eof, print_fn=out.append)

    assert any("Goodbye" in line for line in out)


def test_ctrl_c_exits_cleanly():
    def raise_interrupt(prompt):
        raise KeyboardInterrupt

    out = []
    run_chat(ChatSession(generate=FakeGenerate()), input_fn=raise_interrupt, print_fn=out.append)

    assert any("Goodbye" in line for line in out)
