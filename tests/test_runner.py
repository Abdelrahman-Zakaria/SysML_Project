import json
import os
import socket
import unittest
import urllib.error
from unittest import mock

from teacher_intent import client
from teacher_intent.client import (AnthropicProvider, FakeProvider, ProviderError, ProviderResponse,
                                   TeacherTimeout)
from teacher_intent.config import Config
from teacher_intent.runner import estimate_cost, run_one
from tests.test_validate import VALID

CFG = Config("fake", "test-model", 5.0, 500, price_in_per_mtok=3.0, price_out_per_mtok=15.0)
REQ = {"id": "t-1", "text": "Build a fictional thing."}


def run(behavior):
    return run_one(REQ, FakeProvider(behavior), CFG)


class RunnerOutcomes(unittest.TestCase):
    def test_ok_records_everything(self):
        rec = run(lambda s, u: ProviderResponse(json.dumps(VALID),
                                                {"input_tokens": 1000, "output_tokens": 200}, "test-model-x"))
        self.assertEqual(rec["status"], "ok")
        self.assertEqual(rec["model_id"], "test-model")
        self.assertEqual(rec["model_id_reported"], "test-model-x")
        self.assertEqual(rec["prompt_version"], "intent-prompt.v1")
        self.assertEqual(rec["usage"], {"input_tokens": 1000, "output_tokens": 200})
        self.assertAlmostEqual(rec["estimated_cost_usd"], 0.006)  # 1000*3/1e6 + 200*15/1e6
        self.assertIsInstance(rec["duration_s"], float)
        self.assertEqual(rec["intent"]["title"], VALID["title"])

    def test_malformed_json_is_rejected_and_recorded(self):
        rec = run(lambda s, u: ProviderResponse("not json", {"input_tokens": 10, "output_tokens": 5}))
        self.assertEqual(rec["status"], "invalid_json")
        self.assertIsNone(rec["intent"])
        self.assertEqual(rec["raw_output_excerpt"], "not json")
        self.assertIsNotNone(rec["estimated_cost_usd"])  # tokens were still spent

    def test_schema_violation_is_rejected_and_recorded(self):
        bad = dict(VALID, intent="nope")
        rec = run(lambda s, u: ProviderResponse(json.dumps(bad), None))
        self.assertEqual(rec["status"], "schema_violation")
        self.assertIsNone(rec["intent"])

    def test_timeout(self):
        def boom(s, u):
            raise TeacherTimeout("slow")
        rec = run(boom)
        self.assertEqual(rec["status"], "timeout")
        self.assertIsNone(rec["usage"])

    def test_provider_error(self):
        def boom(s, u):
            raise ProviderError("HTTP 529", status=529)
        rec = run(boom)
        self.assertEqual(rec["status"], "provider_error")
        self.assertIn("529", rec["error_detail"])

    def test_missing_usage_gives_null_cost_not_a_guess(self):
        rec = run(lambda s, u: ProviderResponse(json.dumps(VALID), None))
        self.assertEqual(rec["status"], "ok")
        self.assertIsNone(rec["estimated_cost_usd"])

    def test_cost_math(self):
        self.assertEqual(estimate_cost({"input_tokens": 1_000_000, "output_tokens": 1_000_000}, CFG), 18.0)


class AnthropicProviderBehavior(unittest.TestCase):
    def test_missing_key_fails_before_any_network_call(self):
        with mock.patch.dict(os.environ, {}, clear=True), \
             mock.patch.object(client.urllib.request, "urlopen") as urlopen:
            with self.assertRaises(ProviderError):
                AnthropicProvider("m", 5, 100)
            urlopen.assert_not_called()

    def _provider(self):
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key-not-real"}):
            return AnthropicProvider("m", 5, 100)

    def test_socket_timeout_maps_to_teacher_timeout(self):
        p = self._provider()
        with mock.patch.object(client.urllib.request, "urlopen", side_effect=socket.timeout()):
            with self.assertRaises(TeacherTimeout):
                p.complete("s", "u")

    def test_wrapped_urlerror_timeout_maps_to_teacher_timeout(self):
        p = self._provider()
        with mock.patch.object(client.urllib.request, "urlopen",
                               side_effect=urllib.error.URLError(socket.timeout())):
            with self.assertRaises(TeacherTimeout):
                p.complete("s", "u")

    def test_http_error_maps_to_provider_error_with_status(self):
        p = self._provider()
        err = urllib.error.HTTPError("u", 429, "rate", {}, None)
        with mock.patch.object(client.urllib.request, "urlopen", side_effect=err):
            with self.assertRaises(ProviderError) as cm:
                p.complete("s", "u")
        self.assertEqual(cm.exception.status, 429)

    def test_parses_text_and_usage(self):
        p = self._provider()
        body = json.dumps({"model": "m-1", "content": [{"type": "text", "text": "{}"}],
                           "usage": {"input_tokens": 7, "output_tokens": 3}}).encode()
        resp = mock.MagicMock()
        resp.__enter__.return_value.read.return_value = body
        with mock.patch.object(client.urllib.request, "urlopen", return_value=resp):
            out = p.complete("s", "u")
        self.assertEqual((out.text, out.usage, out.model_id), ("{}", {"input_tokens": 7, "output_tokens": 3}, "m-1"))


if __name__ == "__main__":
    unittest.main()
