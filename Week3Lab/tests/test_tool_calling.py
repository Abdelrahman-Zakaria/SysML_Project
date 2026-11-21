"""Unit tests for the Tool Calling layer. Run: python -m unittest discover -s tests -p "test_tool_calling.py" -v"""

import json
import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tool_calling import ToolDispatcher, ToolError, ToolRegistry, build_default_registry
from tool_calling import errors as E
from tool_calling.registry import MAX_RAW_CALL_CHARS
from tool_calling.schema import validate_arguments, validate_schema_definition
from tool_calling.tools import ToolSpec


def call(name, **arguments):
    return {"name": name, "arguments": arguments}


class DispatcherTestCase(unittest.TestCase):
    def setUp(self):
        self.d = ToolDispatcher()

    def assertFails(self, result, code):
        self.assertFalse(result.ok)
        self.assertIsNone(result.data)
        self.assertEqual(result.error.code, code, result.error.message)

    def assertOk(self, result):
        self.assertTrue(result.ok, result.error)
        self.assertIsNone(result.error)
        return result.data


class TestRegistry(unittest.TestCase):
    def test_default_registry_has_exactly_three_tools(self):
        self.assertEqual(
            build_default_registry().names(),
            ["check_condition", "get_metadata", "list_available_items"],
        )

    def test_describe_exposes_name_description_schema(self):
        for entry in build_default_registry().describe():
            self.assertEqual(set(entry), {"name", "description", "input_schema"})
            self.assertTrue(entry["description"])
            self.assertEqual(entry["input_schema"]["type"], "object")
            self.assertIs(entry["input_schema"]["additionalProperties"], False)
            json.dumps(entry)  # must be JSON-serializable

    def test_duplicate_registration_rejected(self):
        reg = build_default_registry()
        with self.assertRaises(ValueError):
            reg.register(reg.get("get_metadata"))

    def test_bad_registrations_rejected(self):
        schema = {"type": "object", "properties": {}, "required": [], "additionalProperties": False}
        reg = ToolRegistry()
        with self.assertRaises(ValueError):
            reg.register(ToolSpec("", "d", schema, lambda: None))
        with self.assertRaises(ValueError):
            reg.register(ToolSpec("x" * 65, "d", schema, lambda: None))
        with self.assertRaises(ValueError):
            reg.register(ToolSpec("ok", "d", schema, "not callable"))

    def test_malformed_schema_definitions_rejected(self):
        with self.assertRaises(ValueError):
            validate_schema_definition({"type": "array"})
        with self.assertRaises(ValueError):
            validate_schema_definition({"type": "object", "properties": {}})  # additionalProperties missing
        with self.assertRaises(ValueError):
            validate_schema_definition(
                {"type": "object", "properties": {"a": {"type": "list"}}, "additionalProperties": False}
            )
        with self.assertRaises(ValueError):
            validate_schema_definition(
                {"type": "object", "properties": {}, "required": ["ghost"], "additionalProperties": False}
            )

    def test_tool_error_rejects_unknown_code(self):
        with self.assertRaises(ValueError):
            ToolError("MADE_UP", "x")


class TestListAvailableItems(DispatcherTestCase):
    def test_defaults_return_all_items_sorted(self):
        data = self.assertOk(self.d.dispatch(call("list_available_items")))
        ids = [i["item_id"] for i in data["items"]]
        self.assertEqual(ids, sorted(ids))
        self.assertEqual((data["total"], data["returned"], data["offset"]), (8, 8, 0))
        self.assertFalse(data["has_more"])

    def test_category_filter(self):
        data = self.assertOk(self.d.dispatch(call("list_available_items", category="books")))
        self.assertEqual(data["total"], 3)
        self.assertTrue(all(i["category"] == "books" for i in data["items"]))

    def test_pagination(self):
        first = self.assertOk(self.d.dispatch(call("list_available_items", limit=3)))
        self.assertEqual(first["returned"], 3)
        self.assertTrue(first["has_more"])
        last = self.assertOk(self.d.dispatch(call("list_available_items", limit=3, offset=6)))
        self.assertEqual(last["returned"], 2)
        self.assertFalse(last["has_more"])

    def test_offset_past_end_is_empty_not_error(self):
        data = self.assertOk(self.d.dispatch(call("list_available_items", offset=100)))
        self.assertEqual((data["returned"], data["has_more"]), (0, False))

    def test_is_deterministic(self):
        a = self.d.dispatch(call("list_available_items", limit=5)).to_dict()
        b = self.d.dispatch(call("list_available_items", limit=5)).to_dict()
        self.assertEqual(a, b)

    def test_rejections(self):
        cases = [
            (dict(limit=0), E.INVALID_VALUE),
            (dict(limit=21), E.INVALID_VALUE),
            (dict(limit=-1), E.INVALID_VALUE),
            (dict(offset=-1), E.INVALID_VALUE),
            (dict(offset=1001), E.INVALID_VALUE),
            (dict(limit="5"), E.INVALID_TYPE),
            (dict(limit=2.5), E.INVALID_TYPE),
            (dict(limit=True), E.INVALID_TYPE),
            (dict(limit=None), E.INVALID_TYPE),
            (dict(category=5), E.INVALID_TYPE),
            (dict(category="toys"), E.INVALID_VALUE),
            (dict(category="Books"), E.INVALID_VALUE),
            (dict(sort="asc"), E.UNEXPECTED_ARGUMENT),
        ]
        for args, code in cases:
            with self.subTest(args=args):
                self.assertFails(self.d.dispatch(call("list_available_items", **args)), code)


class TestGetMetadata(DispatcherTestCase):
    def test_success(self):
        data = self.assertOk(self.d.dispatch(call("get_metadata", item_id="book-002")))
        self.assertEqual(data["name"], "Deep Learning Basics")
        self.assertEqual(data["tags"], ["ai", "ml"])
        self.assertTrue(data["on_sale"])
        json.dumps(data)

    def test_every_listed_item_has_metadata(self):
        listing = self.assertOk(self.d.dispatch(call("list_available_items")))
        for item in listing["items"]:
            with self.subTest(item=item["item_id"]):
                data = self.assertOk(self.d.dispatch(call("get_metadata", item_id=item["item_id"])))
                self.assertEqual(data["item_id"], item["item_id"])

    def test_missing_record(self):
        self.assertFails(self.d.dispatch(call("get_metadata", item_id="book-999")), E.NOT_FOUND)

    def test_rejections(self):
        cases = [
            ({}, E.MISSING_ARGUMENT),
            (dict(item_id="book-001", extra=1), E.UNEXPECTED_ARGUMENT),
            (dict(item_id=1), E.INVALID_TYPE),
            (dict(item_id=None), E.INVALID_TYPE),
            (dict(item_id=["book-001"]), E.INVALID_TYPE),
            (dict(item_id=""), E.INVALID_VALUE),
            (dict(item_id="BOOK-001"), E.INVALID_VALUE),
            (dict(item_id="book-1"), E.INVALID_VALUE),
            (dict(item_id="book-001\n"), E.INVALID_VALUE),
            (dict(item_id="../etc/passwd"), E.INVALID_VALUE),
            (dict(item_id="book-001; DROP TABLE"), E.INVALID_VALUE),
            (dict(item_id="a" * 5000), E.INVALID_VALUE),
        ]
        for args, code in cases:
            with self.subTest(args=args):
                self.assertFails(self.d.dispatch(call("get_metadata", **args)), code)


class TestCheckCondition(DispatcherTestCase):
    def check(self, item_id, condition, **extra):
        return self.d.dispatch(call("check_condition", item_id=item_id, condition=condition, **extra))

    def test_in_stock(self):
        self.assertTrue(self.assertOk(self.check("book-001", "in_stock"))["satisfied"])
        out = self.assertOk(self.check("book-003", "in_stock"))
        self.assertFalse(out["satisfied"])
        self.assertEqual(out["observed"], 0)

    def test_on_sale(self):
        self.assertTrue(self.assertOk(self.check("elec-002", "on_sale"))["satisfied"])
        self.assertFalse(self.assertOk(self.check("elec-001", "on_sale"))["satisfied"])

    def test_low_stock_default_and_custom_threshold(self):
        out = self.assertOk(self.check("book-002", "low_stock"))  # stock 3, default 5
        self.assertTrue(out["satisfied"])
        self.assertEqual(out["threshold"], 5)
        self.assertFalse(self.assertOk(self.check("book-002", "low_stock", threshold=2))["satisfied"])
        self.assertFalse(self.assertOk(self.check("book-003", "low_stock"))["satisfied"])  # stock 0 is out, not low
        self.assertFalse(self.assertOk(self.check("elec-001", "low_stock"))["satisfied"])

    def test_price_below_is_strict(self):
        self.assertTrue(self.assertOk(self.check("elec-003", "price_below", threshold=20))["satisfied"])
        self.assertFalse(self.assertOk(self.check("elec-003", "price_below", threshold=19.99))["satisfied"])
        self.assertFalse(self.assertOk(self.check("elec-003", "price_below", threshold=10))["satisfied"])

    def test_missing_record(self):
        self.assertFails(self.check("stat-999", "in_stock"), E.NOT_FOUND)

    def test_rejections(self):
        cases = [
            (dict(condition="in_stock"), E.MISSING_ARGUMENT),
            (dict(item_id="book-001"), E.MISSING_ARGUMENT),
            (dict(item_id="book-001", condition="price_below"), E.MISSING_ARGUMENT),
            (dict(item_id="book-001", condition="in_stock", threshold=1), E.INVALID_VALUE),
            (dict(item_id="book-001", condition="on_sale", threshold=0), E.INVALID_VALUE),
            (dict(item_id="book-001", condition="exploded"), E.INVALID_VALUE),
            (dict(item_id="book-001", condition="__import__('os')"), E.INVALID_VALUE),
            (dict(item_id="book-001", condition="stock > 0"), E.INVALID_VALUE),
            (dict(item_id="book-001", condition=5), E.INVALID_TYPE),
            (dict(item_id="book-001", condition="low_stock", threshold="5"), E.INVALID_TYPE),
            (dict(item_id="book-001", condition="low_stock", threshold=True), E.INVALID_TYPE),
            (dict(item_id="book-001", condition="low_stock", threshold=-1), E.INVALID_VALUE),
            (dict(item_id="book-001", condition="low_stock", threshold=10**9), E.INVALID_VALUE),
            (dict(item_id="book-001", condition="low_stock", threshold=math.nan), E.INVALID_VALUE),
            (dict(item_id="book-001", condition="low_stock", threshold=math.inf), E.INVALID_VALUE),
            (dict(item_id="nope", condition="in_stock"), E.INVALID_VALUE),
            (dict(item_id="book-001", condition="in_stock", mode="x"), E.UNEXPECTED_ARGUMENT),
        ]
        for args, code in cases:
            with self.subTest(args=args):
                self.assertFails(self.d.dispatch(call("check_condition", **args)), code)


class TestDispatcherCallFormat(DispatcherTestCase):
    def test_unknown_and_near_miss_tool_names(self):
        for name in ["delete_all", "GET_METADATA", "get_metadata ", "get-metadata", "__import__", "eval", "os.system"]:
            with self.subTest(name=name):
                self.assertFails(self.d.dispatch({"name": name, "arguments": {}}), E.UNKNOWN_TOOL)

    def test_malformed_calls(self):
        cases = [
            None, 42, "get_metadata", [], [("name", "x")],
            {}, {"arguments": {}}, {"name": None}, {"name": ""}, {"name": 5},
            {"name": "get_metadata", "arguments": []},
            {"name": "get_metadata", "arguments": "item_id=book-001"},
            {"name": "get_metadata", "arguments": None},
            {"name": "get_metadata", "arguments": {1: "x"}},
            {"name": "get_metadata", "arguments": {}, "extra": True},
        ]
        for bad in cases:
            with self.subTest(call=bad):
                self.assertFails(self.d.dispatch(bad), E.INVALID_CALL_FORMAT)

    def test_missing_arguments_key_means_empty_arguments(self):
        self.assertOk(self.d.dispatch({"name": "list_available_items"}))
        self.assertFails(self.d.dispatch({"name": "get_metadata"}), E.MISSING_ARGUMENT)

    def test_long_tool_name_is_truncated_in_error(self):
        res = self.d.dispatch({"name": "x" * 1000, "arguments": {}})
        self.assertFails(res, E.UNKNOWN_TOOL)
        self.assertLessEqual(len(res.tool), 64)

    def test_arguments_are_not_mutated(self):
        args = {"limit": 2}
        self.d.dispatch({"name": "list_available_items", "arguments": args})
        self.assertEqual(args, {"limit": 2})

    def test_internal_errors_are_contained_and_not_leaked(self):
        def boom():
            raise RuntimeError("secret internal detail")

        schema = {"type": "object", "properties": {}, "required": [], "additionalProperties": False}
        reg = ToolRegistry([ToolSpec("boom", "always fails", schema, boom)])
        res = ToolDispatcher(reg).dispatch(call("boom"))
        self.assertFails(res, E.INTERNAL_ERROR)
        self.assertNotIn("secret", res.error.message)

    def test_handler_returning_untyped_value_is_internal_error(self):
        schema = {"type": "object", "properties": {}, "required": [], "additionalProperties": False}
        reg = ToolRegistry([ToolSpec("raw", "returns dict", schema, lambda: {"a": 1})])
        self.assertFails(ToolDispatcher(reg).dispatch(call("raw")), E.INTERNAL_ERROR)

    def test_results_are_json_serializable(self):
        for c in [call("get_metadata", item_id="book-001"), call("get_metadata", item_id="zzz"), {"name": 1}]:
            json.dumps(self.d.dispatch(c).to_dict())


class TestDispatchJson(DispatcherTestCase):
    def test_valid_json(self):
        raw = json.dumps(call("get_metadata", item_id="stat-002"))
        self.assertEqual(self.assertOk(self.d.dispatch_json(raw))["name"], "Gel Pen Set (10)")

    def test_invalid_inputs(self):
        for raw in ["", "{", "not json", '{"name": "get_metadata", "arguments": ', "NaN"]:
            with self.subTest(raw=raw):
                self.assertFails(self.d.dispatch_json(raw), E.INVALID_CALL_FORMAT)

    def test_json_that_is_not_an_object(self):
        for raw in ["[]", "42", '"get_metadata"', "null", "true"]:
            with self.subTest(raw=raw):
                self.assertFails(self.d.dispatch_json(raw), E.INVALID_CALL_FORMAT)

    def test_non_string_input(self):
        self.assertFails(self.d.dispatch_json(None), E.INVALID_CALL_FORMAT)
        self.assertFails(self.d.dispatch_json({"name": "get_metadata"}), E.INVALID_CALL_FORMAT)

    def test_oversized_input_rejected(self):
        self.assertFails(self.d.dispatch_json(" " * (MAX_RAW_CALL_CHARS + 1)), E.INVALID_CALL_FORMAT)

    def test_deeply_nested_json_does_not_crash(self):
        self.assertFalse(self.d.dispatch_json("[" * 5000 + "]" * 5000).ok)


class TestSchemaValidator(unittest.TestCase):
    SCHEMA = {
        "type": "object",
        "properties": {
            "n": {"type": "integer", "minimum": 1, "maximum": 3, "default": 2},
            "s": {"type": "string", "minLength": 2, "maxLength": 4},
        },
        "required": [],
        "additionalProperties": False,
    }

    def test_defaults_applied_without_mutating_input(self):
        given = {"s": "ab"}
        out = validate_arguments(self.SCHEMA, given)
        self.assertEqual(out, {"s": "ab", "n": 2})
        self.assertEqual(given, {"s": "ab"})

    def test_length_bounds(self):
        for s in ["a", "abcde"]:
            with self.subTest(s=s), self.assertRaises(ToolError) as cm:
                validate_arguments(self.SCHEMA, {"s": s})
            self.assertEqual(cm.exception.code, E.INVALID_VALUE)

    def test_error_order_extra_then_missing_then_type_then_value(self):
        schema = {
            "type": "object",
            "properties": {"a": {"type": "integer", "minimum": 5}},
            "required": ["a"],
            "additionalProperties": False,
        }
        order = [
            ({"zzz": 1}, E.UNEXPECTED_ARGUMENT),
            ({}, E.MISSING_ARGUMENT),
            ({"a": "x"}, E.INVALID_TYPE),
            ({"a": 1}, E.INVALID_VALUE),
        ]
        for args, code in order:
            with self.subTest(args=args), self.assertRaises(ToolError) as cm:
                validate_arguments(schema, args)
            self.assertEqual(cm.exception.code, code)


if __name__ == "__main__":
    unittest.main()
