import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from week3_2300215_agent.agent import run_agent
from week3_2300215_agent.tools import dispatch_tool


class TestAgentExitGate(unittest.TestCase):
    """Verifies tool allowlisting, argument validation, missing data handling, and crash safety."""

    def test_1_fabricated_tool_name_rejected(self):
        def fake_llm(messages):
            if len(messages) == 2:
                return {"tool_calls": [{"id": "c1", "name": "delete_sysml_model", "args": {}}]}
            return {"content": "Cannot run unknown tool."}

        outcome = run_agent("Delete everything", ask_llm=fake_llm)
        tool_msg = json.loads(outcome["messages"][3]["content"])

        self.assertEqual(tool_msg["status"], "error")
        self.assertEqual(tool_msg["code"], "UNKNOWN_TOOL")

    def test_2_invalid_argument_rejected(self):
        bad_id = dispatch_tool("get_element_details", {"element_id": "BatteryPack"})
        bad_mass = dispatch_tool("validate_operation", {"target_id": "BLK-204", "proposed_mass_kg": -5})

        self.assertEqual(bad_id["status"], "error")
        self.assertEqual(bad_id["code"], "INVALID_ARGS")
        self.assertEqual(bad_mass["status"], "error")
        self.assertEqual(bad_mass["code"], "INVALID_ARGS")

    def test_3_missing_evidence_returns_not_found(self):
        res = dispatch_tool("get_element_details", {"element_id": "REQ-999"})

        self.assertEqual(res["status"], "error")
        self.assertEqual(res["code"], "NOT_FOUND")

    def test_4_tool_failure_caught_cleanly(self):
        with patch("week3_2300215_agent.tools.load_model", side_effect=RuntimeError("Model file unreadable")):
            res = dispatch_tool("list_elements", {})

        self.assertEqual(res["status"], "error")
        self.assertEqual(res["code"], "TOOL_ERROR")
        self.assertIn("Model file unreadable", res["message"])

    def test_5_valid_end_to_end_run(self):
        def fake_llm(messages):
            if len(messages) == 2:
                return {
                    "tool_calls": [
                        {"id": "c1", "name": "validate_operation", "args": {"target_id": "BLK-204", "proposed_mass_kg": 42.0}}
                    ]
                }
            return {"content": "BLK-204 at 42.0 kg satisfies REQ-101 (limit 50.0 kg)."}

        outcome = run_agent("Check 42 kg for BLK-204", ask_llm=fake_llm)
        tool_msg = json.loads(outcome["messages"][3]["content"])

        self.assertEqual(outcome["status"], "completed")
        self.assertTrue(tool_msg["valid"])


if __name__ == "__main__":
    unittest.main()