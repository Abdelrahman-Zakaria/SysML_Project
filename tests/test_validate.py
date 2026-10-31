import copy
import json
import unittest

from teacher_intent.validate import InvalidJSON, SchemaViolation, parse_intent

VALID = {
    "schema_version": "intent.v1", "intent": "create_project",
    "title": "Overdue loan report", "summary": "CLI that lists overdue library loans.",
    "language": "Python",
    "components": [{"name": "parser", "responsibility": "Reads the CSV"}],
    "acceptance_criteria": ["Lists overdue loans grouped by borrower"],
    "constraints": ["Synthetic data only"], "risk_flags": ["none"],
}


def mutated(**changes):
    d = copy.deepcopy(VALID)
    for k, v in changes.items():
        if v is KeyError:
            d.pop(k)
        else:
            d[k] = v
    return json.dumps(d)


class ValidIntent(unittest.TestCase):
    def test_valid_passes(self):
        self.assertEqual(parse_intent(json.dumps(VALID))["intent"], "create_project")

    def test_optional_language_may_be_omitted(self):
        parse_intent(mutated(language=KeyError))


class MalformedOutputIsRejected(unittest.TestCase):
    def assertInvalidJSON(self, text):
        with self.assertRaises(InvalidJSON):
            parse_intent(text)

    def assertSchema(self, text):
        with self.assertRaises(SchemaViolation):
            parse_intent(text)

    # --- not JSON at all
    def test_plain_prose(self):
        self.assertInvalidJSON("Sure! Here is your plan: build a CLI.")

    def test_truncated_json(self):
        self.assertInvalidJSON(json.dumps(VALID)[:-15])

    def test_markdown_fenced_json_is_rejected(self):
        self.assertInvalidJSON("```json\n" + json.dumps(VALID) + "\n```")

    def test_empty_output(self):
        self.assertInvalidJSON("")

    def test_none_output(self):
        self.assertInvalidJSON(None)

    # --- JSON but wrong shape
    def test_top_level_array(self):
        self.assertSchema(json.dumps([VALID]))

    def test_top_level_string(self):
        self.assertSchema('"hello"')

    def test_missing_required_field(self):
        self.assertSchema(mutated(summary=KeyError))

    def test_unexpected_extra_field(self):
        self.assertSchema(mutated(shell_command="ls"))

    def test_wrong_schema_version(self):
        self.assertSchema(mutated(schema_version="intent.v2"))

    def test_unknown_intent_value(self):
        self.assertSchema(mutated(intent="delete_everything"))

    def test_wrong_type_for_title(self):
        self.assertSchema(mutated(title=123))

    def test_title_too_long(self):
        self.assertSchema(mutated(title="x" * 121))

    def test_empty_components(self):
        self.assertSchema(mutated(components=[]))

    def test_component_with_extra_key(self):
        self.assertSchema(mutated(components=[{"name": "a", "responsibility": "b", "code": "x"}]))

    def test_too_many_acceptance_criteria(self):
        self.assertSchema(mutated(acceptance_criteria=["ok"] * 11))

    def test_bad_risk_flag(self):
        self.assertSchema(mutated(risk_flags=["yolo"]))

    # --- intent must not smuggle in executable code
    def test_code_fence_inside_field(self):
        self.assertSchema(mutated(summary="Do this:\n```python\nprint(1)\n```"))

    def test_python_function_inside_field(self):
        self.assertSchema(mutated(summary="First line\ndef run():\n    pass"))

    def test_shell_destruction_inside_field(self):
        self.assertSchema(mutated(constraints=["run rm -rf / first"]))


if __name__ == "__main__":
    unittest.main()
