import copy
import json
import unittest

from intent_teacher.providers import _FAKE_INTENT
from intent_teacher.schema import (IntentValidationError, InvalidJSONError,
                                   parse_intent_json, validate_intent)


def good():
    return copy.deepcopy(_FAKE_INTENT)


class ValidIntent(unittest.TestCase):
    def test_good_intent_passes(self):
        self.assertEqual(validate_intent(good())["schema_version"], "intent.v1")

    def test_clarification_flow_passes(self):
        d = good(); d["needs_clarification"] = True; d["clarifying_questions"] = ["What kind of app?"]
        validate_intent(d)


class MalformedJSONRejected(unittest.TestCase):
    def test_rejects(self):
        cases = {
            "empty": "",
            "whitespace": "   \n",
            "prose": "Sure! Here is your intent.",
            "truncated": '{"schema_version": "intent.v1", ',
            "fenced": "```json\n" + json.dumps(good()) + "\n```",
            "prose_then_json": "Here you go: " + json.dumps(good()),
        }
        for name, text in cases.items():
            with self.subTest(name), self.assertRaises(InvalidJSONError):
                parse_intent_json(text)


class MalformedIntentRejected(unittest.TestCase):
    def assert_rejected(self, obj, fragment=None):
        with self.assertRaises(IntentValidationError) as ctx:
            validate_intent(obj)
        if fragment:
            self.assertIn(fragment, str(ctx.exception))

    def test_not_an_object(self):
        for value in ([], "text", 42, None):
            with self.subTest(value):
                self.assert_rejected(value, "expected JSON object")

    def test_missing_keys(self):
        for key in list(good()):
            with self.subTest(key):
                d = good(); del d[key]
                self.assert_rejected(d, f"missing key: {key}")

    def test_unexpected_key_such_as_code(self):
        d = good(); d["code"] = "print('hi')"
        self.assert_rejected(d, "unexpected key: code")

    def test_wrong_schema_version(self):
        d = good(); d["schema_version"] = "intent.v2"
        self.assert_rejected(d, "schema_version")

    def test_bad_enums(self):
        d = good(); d["risk_level"] = "catastrophic"
        self.assert_rejected(d, "risk_level")
        d = good(); d["project_type"] = "spaceship"
        self.assert_rejected(d, "project_type")

    def test_wrong_types(self):
        for key, bad in [("goal", 5), ("components", "x"), ("constraints", "x"),
                         ("needs_clarification", "yes"), ("clarifying_questions", None)]:
            with self.subTest(key):
                d = good(); d[key] = bad
                self.assert_rejected(d)

    def test_empty_components(self):
        d = good(); d["components"] = []
        self.assert_rejected(d, "components")

    def test_component_shape(self):
        d = good(); d["components"] = [{"name": "x"}]
        self.assert_rejected(d, "missing key purpose")
        d = good(); d["components"] = [{"name": "x", "purpose": "y", "extra": 1}]
        self.assert_rejected(d, "unexpected key extra")

    def test_code_in_strings_rejected(self):
        for text in ["```python\nprint(1)\n```", "#!/bin/sh\nrm -rf /",
                     "import os\nos.system('x')", "def run():\n    pass"]:
            with self.subTest(text):
                d = good(); d["goal"] = text
                self.assert_rejected(d, "looks like code")

    def test_overlong_goal(self):
        d = good(); d["goal"] = "x" * 301
        self.assert_rejected(d, "longer than 300")

    def test_clarification_consistency(self):
        d = good(); d["needs_clarification"] = True
        self.assert_rejected(d, "required when needs_clarification")
        d = good(); d["clarifying_questions"] = ["Why?"]
        self.assert_rejected(d, "must be empty")

    def test_reports_all_errors_at_once(self):
        d = good(); d["risk_level"] = "x"; d["code"] = "y"
        with self.assertRaises(IntentValidationError) as ctx:
            validate_intent(d)
        self.assertGreaterEqual(len(ctx.exception.errors), 2)


if __name__ == "__main__":
    unittest.main()
