
from typing import Any

import requests


def get_json(url: str, timeout: float = 10.0) -> Any:
    """Send a GET request and return the response data as JSON.
    """
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    return response.json()

