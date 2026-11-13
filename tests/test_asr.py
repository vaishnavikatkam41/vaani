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

    def test_uses_whisper_without_key(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("SARVAM_API_KEY", None)
            with mock.patch.object(asr, "_whisper", return_value="whisper text") as w:
                self.assertEqual(asr.transcribe(str(self.path)), "whisper text")
                w.assert_called_once()

    def test_uses_sarvam_with_key(self):
        with mock.patch.dict(os.environ, {"SARVAM_API_KEY": "k"}):
            with mock.patch.object(asr, "_sarvam", return_value="telugu text") as s, \
                    mock.patch.object(asr, "_whisper") as w:
                self.assertEqual(asr.transcribe(str(self.path)), "telugu text")
                s.assert_called_once()
                w.assert_not_called()

    def test_falls_back_to_whisper_when_sarvam_fails(self):
        with mock.patch.dict(os.environ, {"SARVAM_API_KEY": "k"}):
            with mock.patch.object(asr, "_sarvam", side_effect=RuntimeError("no net")), \
                    mock.patch.object(asr, "_whisper", return_value="backup") as w:
                self.assertEqual(asr.transcribe(str(self.path)), "backup")
                w.assert_called_once()


if __name__ == "__main__":
    unittest.main()
