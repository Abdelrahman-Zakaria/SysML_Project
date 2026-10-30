
import pytest
import requests

from unittest.mock import Mock
from app import get_json


TEST_URL = "https://jsonplaceholder.typicode.com/todos/1"


# Test 1: Successful HTTP response
def test_get_json_success(monkeypatch):
    expected_data = {
        "userId": 1,
        "id": 1,
        "title": "delectus aut autem",
        "completed": False
    }

    mock_response = Mock()
    mock_response.json.return_value = expected_data

    def mock_get(url, timeout):
        assert url == TEST_URL
        assert timeout == 10.0
        return mock_response

    monkeypatch.setattr("app.requests.get", mock_get)

    result = get_json(TEST_URL)

    assert result == expected_data
    mock_response.raise_for_status.assert_called_once()
    mock_response.json.assert_called_once()


# Test 2: HTTP error
def test_get_json_http_error(monkeypatch):
    mock_response = Mock()

    mock_response.raise_for_status.side_effect = (
        requests.exceptions.HTTPError("404 Not Found")
    )

    def mock_get(url, timeout):
        return mock_response

    monkeypatch.setattr("app.requests.get", mock_get)

    with pytest.raises(requests.exceptions.HTTPError):
        get_json(TEST_URL)


# Test 3: Timeout error
def test_get_json_timeout(monkeypatch):

    def mock_get(url, timeout):
        raise requests.exceptions.Timeout("Request timed out")

    monkeypatch.setattr("app.requests.get", mock_get)

    with pytest.raises(requests.exceptions.Timeout):
        get_json(TEST_URL)
