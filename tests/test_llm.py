"""Tests the AI answer writer step with a PRETEND model (no internet, no key)."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import httpx

from src import ingest, llm
from src.pipeline import Vaani

FIXTURES = Path(__file__).parent / "fixtures"
QUESTION = "How should I care for the newborn umbilical cord?"


def make_vaani():
    with tempfile.TemporaryDirectory() as tmp:
        chunks = ingest.ingest(FIXTURES, Path(tmp) / "n.csv", Path(tmp) / "c.json")
    return Vaani(chunks=chunks, log_unanswered=False)


class TestLlmStep(unittest.TestCase):
    def setUp(self):
        self.vaani = make_vaani()

    def test_ai_telugu_answer_is_used_and_sources_kept(self):
        with mock.patch.object(llm, "available", return_value=True), \
                mock.patch.object(llm, "write_answer", return_value="బొడ్డు తాడును పొడిగా ఉంచండి."):
            result = self.vaani.ask(QUESTION)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["language"], "te")
        self.assertIn("బొడ్డు తాడు", result["answer"])
        self.assertTrue(result["sources"])

    def test_ai_says_no_answer_means_idk(self):
        with mock.patch.object(llm, "available", return_value=True), \
                mock.patch.object(llm, "write_answer", return_value=None):
            result = self.vaani.ask(QUESTION)
        self.assertEqual(result["status"], "idk")

    def test_ai_failure_falls_back_to_baseline(self):
        with mock.patch.object(llm, "available", return_value=True), \
                mock.patch.object(llm, "write_answer", side_effect=RuntimeError("no internet")):
            result = self.vaani.ask(QUESTION)
        self.assertEqual(result["status"], "ok")

    def test_ai_dose_sentence_is_still_removed(self):
        with mock.patch.object(llm, "available", return_value=True), \
                mock.patch.object(llm, "write_answer", return_value="Give 500 mg of paracetamol twice a day."):
            result = self.vaani.ask(QUESTION)
        self.assertNotIn("500", result["answer"])


class TestSarvamRequest(unittest.TestCase):
    def test_request_shape_and_reply(self):
        seen = {}

        def handler(request):
            seen["key"] = request.headers.get("api-subscription-key")
            seen["body"] = request.content.decode("utf-8")
            return httpx.Response(200, json={"choices": [{"message": {"content": "జవాబు"}}]})

        client = httpx.Client(transport=httpx.MockTransport(handler))
        with mock.patch.dict(os.environ, {"SARVAM_API_KEY": "k"}), \
                mock.patch("httpx.post", lambda *a, **kw: client.post(*a, **kw)):
            text = llm.write_answer("q?", [{"text": "passage one"}])
        self.assertEqual(text, "జవాబు")
        self.assertEqual(seen["key"], "k")
        self.assertIn("passage one", seen["body"])
        self.assertIn("sarvam-105b", seen["body"])

    def test_no_answer_marker_returns_none(self):
        client = httpx.Client(transport=httpx.MockTransport(
            lambda r: httpx.Response(200, json={"choices": [{"message": {"content": "NO_ANSWER"}}]})))
        with mock.patch.dict(os.environ, {"SARVAM_API_KEY": "k"}), \
                mock.patch("httpx.post", lambda *a, **kw: client.post(*a, **kw)):
            self.assertIsNone(llm.write_answer("q?", [{"text": "p"}]))


if __name__ == "__main__":
    unittest.main()
