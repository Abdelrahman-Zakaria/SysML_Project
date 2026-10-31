import io
import json
import os
import tempfile
import unittest
import urllib.error
from unittest import mock

from intent_teacher.__main__ import main
from intent_teacher.cost import estimate_cost
from intent_teacher.providers import (AnthropicProvider, Completion, ConfigError,
                                      FakeProvider, ProviderError, TeacherTimeout,
                                      _FAKE_INTENT)
from intent_teacher.runner import request_intent

PRICING = {"models": {"fake-teacher-1": {"input_per_mtok": 1.0, "output_per_mtok": 5.0, "as_of": "t"}}}


class Stub:
    name, model = "stub", "fake-teacher-1"
    def __init__(self, result): self.result = result
    def complete(self, system, user, timeout):
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


class RunnerOutcomes(unittest.TestCase):
    def test_success_records_everything(self):
        r = request_intent(FakeProvider(), "x", pricing=PRICING, clock=iter([10.0, 10.5]).__next__)
        self.assertEqual(r.status, "ok")
        self.assertEqual(r.requested_model, "fake-teacher-1")
        self.assertEqual(r.prompt_version, "intent-prompt-v1")
        self.assertEqual(r.duration_s, 0.5)
        self.assertEqual(r.usage, {"input_tokens": 400, "output_tokens": 150})
        self.assertAlmostEqual(r.est_cost_usd, (400 * 1 + 150 * 5) / 1e6)
        self.assertIsNotNone(r.intent)

    def test_timeout(self):
        r = request_intent(Stub(TeacherTimeout("slow")), "x")
        self.assertEqual((r.status, r.intent), ("timeout", None))

    def test_provider_error(self):
        r = request_intent(Stub(ProviderError("HTTP 500", status=500)), "x")
        self.assertEqual((r.status, r.intent), ("provider_error", None))

    def test_invalid_json_rejected(self):
        r = request_intent(FakeProvider("bad_json"), "x", pricing=PRICING)
        self.assertEqual((r.status, r.intent), ("invalid_json", None))
        self.assertIsNotNone(r.usage)  # tokens were still spent; we still record cost
        self.assertIsNotNone(r.est_cost_usd)

    def test_malformed_intent_rejected(self):
        r = request_intent(FakeProvider("malformed"), "x", pricing=PRICING)
        self.assertEqual(r.status, "invalid_intent")
        self.assertIsNone(r.intent)
        self.assertIn("unexpected key: code", r.error_message)

    def test_fenced_json_rejected(self):
        text = "```json\n" + json.dumps(_FAKE_INTENT) + "\n```"
        r = request_intent(Stub(Completion(text, "m", None)), "x")
        self.assertEqual(r.status, "invalid_json")


class Cost(unittest.TestCase):
    def test_missing_usage(self):
        self.assertEqual(estimate_cost(PRICING, ["fake-teacher-1"], None)[0], None)

    def test_missing_price_is_not_guessed(self):
        cost, note = estimate_cost(PRICING, ["unknown"], {"input_tokens": 1, "output_tokens": 1})
        self.assertIsNone(cost)
        self.assertIn("no pricing entry", note)


class AnthropicProviderErrors(unittest.TestCase):
    def setUp(self):
        self.p = AnthropicProvider("some-model", api_key="test-key")

    def test_requires_key_and_model(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ConfigError):
                AnthropicProvider("m")
        with self.assertRaises(ConfigError):
            AnthropicProvider("", api_key="k")

    def test_timeout_mapped(self):
        with mock.patch("urllib.request.urlopen", side_effect=TimeoutError):
            with self.assertRaises(TeacherTimeout):
                self.p.complete("s", "u", 1)
        with mock.patch("urllib.request.urlopen", side_effect=urllib.error.URLError(TimeoutError())):
            with self.assertRaises(TeacherTimeout):
                self.p.complete("s", "u", 1)

    def test_http_error_mapped(self):
        err = urllib.error.HTTPError("u", 529, "overloaded", {}, io.BytesIO(b"busy"))
        with mock.patch("urllib.request.urlopen", side_effect=err):
            with self.assertRaises(ProviderError) as ctx:
                self.p.complete("s", "u", 1)
        self.assertEqual(ctx.exception.status, 529)

    def test_success_parses_text_and_usage(self):
        body = {"model": "some-model-dated", "content": [{"type": "text", "text": "{}"}],
                "usage": {"input_tokens": 3, "output_tokens": 4}}
        resp = mock.MagicMock()
        resp.__enter__.return_value = io.BytesIO(json.dumps(body).encode())
        with mock.patch("urllib.request.urlopen", return_value=resp):
            c = self.p.complete("s", "u", 1)
        self.assertEqual((c.text, c.model_id, c.usage["output_tokens"]), ("{}", "some-model-dated", 4))

    def test_bad_shape_mapped(self):
        resp = mock.MagicMock()
        resp.__enter__.return_value = io.BytesIO(b'{"nope": 1}')
        with mock.patch("urllib.request.urlopen", return_value=resp):
            with self.assertRaises(ProviderError):
                self.p.complete("s", "u", 1)


class CliOffline(unittest.TestCase):
    def run_cli(self, *extra):
        with tempfile.TemporaryDirectory() as d:
            log = os.path.join(d, "runs.jsonl")
            with mock.patch("sys.stdout", new_callable=io.StringIO):
                code = main(["--provider", "fake", "--log", log, *extra])
            with open(log, encoding="utf-8") as fh:
                return code, [json.loads(line) for line in fh]

    def test_ok_exit_zero_and_logged(self):
        code, rows = self.run_cli()
        self.assertEqual((code, rows[0]["status"]), (0, "ok"))

    def test_malformed_exit_nonzero_and_logged(self):
        code, rows = self.run_cli("--fake-mode", "malformed")
        self.assertEqual((code, rows[0]["status"]), (1, "invalid_intent"))

    def test_missing_secret_is_config_error_not_crash(self):
        with mock.patch.dict(os.environ, {}, clear=True), mock.patch("sys.stderr", new_callable=io.StringIO):
            self.assertEqual(main(["--provider", "anthropic", "--model", "m"]), 2)


if __name__ == "__main__":
    unittest.main()
