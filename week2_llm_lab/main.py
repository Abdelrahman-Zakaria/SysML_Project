"""Terminal entry point: run with `python main.py`."""

from typing import Callable

from chat import WELCOME_TEXT, ChatSession


def run_chat(
    session: ChatSession | None = None,
    input_fn: Callable[[str], str] = input,
    print_fn: Callable[[str], None] = print,
) -> None:
    """Read user lines until /exit, Ctrl+C or end of input."""

    session = session or ChatSession()
    print_fn(WELCOME_TEXT)

    while True:
        try:
            line = input_fn("\nYou> ")
        except (EOFError, KeyboardInterrupt):
            print_fn("\nGoodbye!")
            return

        reply, should_exit = session.handle_input(line)
        print_fn(f"\nBot> {reply}")

        if should_exit:
            return


if __name__ == "__main__":
    run_chat()
