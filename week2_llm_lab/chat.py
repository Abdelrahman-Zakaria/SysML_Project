"""
Chat session logic for the SysML requirements chatbot.

ChatSession is independent of the terminal so it can be tested offline:
handle_input() takes one line of text and returns the reply to display.
"""

from typing import Callable

from config import MAX_HISTORY_MESSAGES
from intent_service import LLMRequestError, generate_intent
from models import Intent

HELP_TEXT = """\
Commands:
  /help   Show this help
  /clear  Forget the current conversation
  /json   Show the latest validated Intent as JSON
  /exit   Close the chatbot

I help with SysML / engineering requirement requests. Examples:
  Draft a functional requirement for an elevator that stops at the floor
  selected by the passenger.
  Write a non-functional requirement for the response time of a login page.
If I need more detail I will ask; just answer in your next message."""

UNSUPPORTED_TEXT = (
    "Sorry, that request is outside what I can do. I only help draft "
    "SysML / engineering requirements (functional or non-functional). "
    "I do not write code, run commands or modify project files."
)

WELCOME_TEXT = (
    "SysML Requirements Chatbot. Describe a requirement you want drafted.\n"
    "Type /help for commands."
)


def format_intent(intent: Intent) -> str:
    """Turn a validated Intent into a readable reply."""

    if intent.intent_type == "unsupported":
        return f"Intent: unsupported\n{UNSUPPORTED_TEXT}"

    lines = [
        f"Intent: {intent.intent_type}",
        f"Requirement type: {intent.requirement_type}",
    ]
    if intent.requirement_text:
        lines.append(f"Requirement: {intent.requirement_text}")
    lines.append(
        "Clarification needed: "
        + ("Yes" if intent.clarification_needed else "No")
    )
    if intent.clarification_question:
        lines.append(f"Question: {intent.clarification_question}")
    return "\n".join(lines)


class ChatSession:
    """Holds the conversation history and the latest validated Intent."""

    def __init__(
        self,
        generate: Callable[..., tuple] = generate_intent,
        max_history_messages: int = MAX_HISTORY_MESSAGES,
    ) -> None:
        self._generate = generate
        self.max_history_messages = max_history_messages
        self.history: list[dict[str, str]] = []
        self.last_intent: Intent | None = None
        self.last_metadata: dict | None = None

    def clear(self) -> None:
        """Forget the conversation and the latest Intent."""

        self.history = []
        self.last_intent = None
        self.last_metadata = None

    def _remember_turn(self, user_text: str, intent: Intent) -> None:
        """Store one turn, keeping only the most recent messages."""

        self.history.append({"role": "user", "content": user_text})
        self.history.append(
            {"role": "assistant", "content": intent.model_dump_json()}
        )

        limit = max(2, self.max_history_messages)
        limit -= limit % 2  # keep whole user/assistant pairs
        if len(self.history) > limit:
            self.history = self.history[-limit:]

    def handle_input(self, text: str) -> tuple[str, bool]:
        """
        Process one line of user input.

        Returns (reply_text, should_exit). Never raises for ordinary
        failures: errors are returned as readable messages.
        """

        text = (text or "").strip()

        if not text:
            return "Please type a request, or /help for commands.", False

        if text.startswith("/"):
            return self._handle_command(text.lower())

        try:
            intent, _response, metadata = self._generate(
                text, list(self.history)
            )
        except LLMRequestError as exc:
            return f"Error: {exc}\nYou can try again.", False
        except ValueError as exc:
            return (
                f"Sorry, I could not produce a valid result ({exc}). "
                "Please try again or rephrase your request.",
                False,
            )
        except Exception as exc:  # keep the chatbot alive
            return (
                f"Unexpected error ({type(exc).__name__}: {exc}). "
                "You can try again.",
                False,
            )

        self.last_intent = intent
        self.last_metadata = metadata
        self._remember_turn(text, intent)

        return format_intent(intent), False

    def _handle_command(self, command: str) -> tuple[str, bool]:
        if command == "/help":
            return HELP_TEXT, False
        if command == "/clear":
            self.clear()
            return "Conversation cleared.", False
        if command == "/json":
            if self.last_intent is None:
                return "No Intent yet. Send a request first.", False
            return self.last_intent.model_dump_json(indent=2), False
        if command == "/exit":
            return "Goodbye!", True
        return f"Unknown command: {command}. Type /help.", False
