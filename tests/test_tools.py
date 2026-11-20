from src.tools import (
    list_available_items,
    get_metadata,
    check_condition
)

from src.agent import execute_tool, TOOL_REGISTRY


# TEST 1: Verify that all elevator elements are returned.
def test_list_available_items():
    result = list_available_items()

    assert len(result) == 5
    assert 1 in result
    assert 5 in result


# TEST 2: Verify that valid metadata is retrieved correctly.
def test_get_metadata():
    result = get_metadata(2)

    assert result["name"] == "Motor"
    assert result["type"] == "Part"
    assert result["status"] == "Available"


# TEST 3: Verify that nonexistent elements return an error.
def test_get_invalid_metadata():
    result = get_metadata(99)

    assert "error" in result


# TEST 4: Verify that the available condition works.
def test_check_available():
    result = check_condition(2, "available")

    assert result is True


# TEST 5: Verify that the defined condition works.
def test_check_defined():
    result = check_condition(4, "defined")

    assert result is True


# TEST 6: Verify that unsupported conditions are rejected.
def test_invalid_condition():
    result = check_condition(2, "unknown")

    assert "error" in result


# TEST 7: Verify that fabricated tool names are rejected.
def test_unknown_tool():
    result = execute_tool("delete_elevator", {})

    assert "error" in result


# TEST 8: Verify that invalid arguments are rejected.
def test_invalid_arguments():
    result = execute_tool("get_metadata", {"item_id": -5})

    assert "error" in result
    assert result["error"] == "Invalid arguments"


# TEST 9: Verify that unexpected arguments are rejected.
def test_extra_arguments():
    result = execute_tool(
        "get_metadata",
        {"item_id": 2, "delete": True}
    )

    assert "error" in result


# TEST 10: Verify that tool execution failures are handled.
def test_tool_execution_failure(monkeypatch):

    def failing_tool(item_id):
        raise RuntimeError("Database failure")

    monkeypatch.setitem(
        TOOL_REGISTRY["get_metadata"],
        "function",
        failing_tool
    )

    result = execute_tool("get_metadata", {"item_id": 2})

    assert "error" in result
    assert "Tool execution failed" in result["error"]


# TEST 11: Verify that missing information is reported.
def test_no_evidence():
    result = execute_tool("get_metadata", {"item_id": 99})

    assert "error" in result["result"]