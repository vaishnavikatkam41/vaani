"""Tests the speech-to-text switch (no real models, no internet)."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from src import asr


class TestAsrSwitch(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "q.webm"
        self.path.write_bytes(b"x" * 100)

    def tearDown(self):
        self.tmp.cleanup()

    def test_uses_local_model_without_key(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("SARVAM_API_KEY", None)
            with mock.patch.object(asr, "_local_transcribe", return_value="whisper text") as w:
                self.assertEqual(asr.transcribe(str(self.path)), "whisper text")
                w.assert_called_once()

    def test_uses_sarvam_with_key(self):
        with mock.patch.dict(os.environ, {"SARVAM_API_KEY": "k"}):
            with mock.patch.object(asr, "_sarvam", return_value="telugu text") as s, \
                    mock.patch.object(asr, "_local_transcribe") as w:
                self.assertEqual(asr.transcribe(str(self.path)), "telugu text")
                s.assert_called_once()
                w.assert_not_called()

    def test_falls_back_to_local_when_sarvam_fails(self):
        with mock.patch.dict(os.environ, {"SARVAM_API_KEY": "k"}):
            with mock.patch.object(asr, "_sarvam", side_effect=RuntimeError("no net")), \
                    mock.patch.object(asr, "_local_transcribe", return_value="backup") as w:
                self.assertEqual(asr.transcribe(str(self.path)), "backup")
                w.assert_called_once()

    def test_sarvam_sends_latest_model_and_health_terms_not_a_hint(self):
        sent = {}

        class Reply:
            status_code = 200
            def raise_for_status(self): pass
            def json(self): return {"transcript": "జ్వరం"}

        def fake_post(url, headers, files, data, timeout):
            sent.update(data)
            return Reply()

        with mock.patch.dict(os.environ, {"SARVAM_API_KEY": "k"}), mock.patch("httpx.post", fake_post):
            os.environ.pop("SARVAM_MODEL", None)
            self.assertEqual(asr._sarvam(str(self.path), "k"), "జ్వరం")
        self.assertEqual(sent["model"], "saaras:v4")
        self.assertEqual(sent["language_code"], "te-IN")
        self.assertIn("జ్వరం", sent["keyterms"])
        # The old hint sentence made Whisper copy words; it must never be sent.
        self.assertNotIn(asr.OLD_HINT, str(sent))


if __name__ == "__main__":
    unittest.main()
