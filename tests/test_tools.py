
from tools.list_items import list_available_items
from tools.get_metadata import get_metadata
from tools.check_condition import check_condition


def test_list_requirements():

    result = list_available_items("Requirement")

    assert result["success"] is True
    assert result["count"] == 2


def test_list_blocks():

    result = list_available_items("Block")

    assert result["success"] is True
    assert result["count"] == 2


def test_get_existing_metadata():

    result = get_metadata("REQ-001")

    assert result["success"] is True
    assert result["data"]["name"] == "System shall be reliable"


def test_get_missing_metadata():

    result = get_metadata("REQ-999")

    assert result["success"] is False
    assert result["error"] == "ELEMENT_NOT_FOUND"


def test_check_existing_element():

    result = check_condition("BLK-001", "exists")

    assert result["success"] is True
    assert result["result"] is True


def test_check_attributes():

    result = check_condition("BLK-001", "has_attributes")

    assert result["success"] is True
    assert result["result"] is True


def test_invalid_condition():

    result = check_condition("BLK-001", "is_perfect")

    assert result["success"] is False
    assert result["error"] == "UNSUPPORTED_CONDITION"


def test_invalid_argument_type():

    result = get_metadata(123)

    assert result["success"] is False
    assert result["error"] == "INVALID_ARGUMENT"
