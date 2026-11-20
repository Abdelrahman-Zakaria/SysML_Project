from types import SimpleNamespace
from src import main


def test_max_tool_call_limit(monkeypatch):

    executed_calls = []
    api_requests = []

    def fake_execute_tool(tool_name, arguments):
        executed_calls.append(tool_name)
        return {"result": "Success"}

    def fake_create(**kwargs):
        api_requests.append(1)

        tool_call = SimpleNamespace(
            id=f"call_{len(api_requests)}",
            function=SimpleNamespace(
                name="list_available_items",
                arguments="{}"
            )
        )

        message = SimpleNamespace(
            content=None,
            tool_calls=[tool_call],
            model_dump=lambda **kwargs: {
                "role": "assistant",
                "content": None
            }
        )

        return SimpleNamespace(
            choices=[
                SimpleNamespace(message=message)
            ]
        )

    monkeypatch.setattr(
        main,
        "execute_tool",
        fake_execute_tool
    )

    monkeypatch.setattr(
        main.client.chat.completions,
        "create",
        fake_create
    )

    result = main.run_agent("List elevator elements")

    assert len(executed_calls) == 5
    assert len(api_requests) == 5
    assert result == "Maximum tool-call limit reached."