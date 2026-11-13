"""Tests the app server with a PRETEND microphone and speaker (no big models needed).
Run:  py -m unittest discover -s tests -t . -v
Needs: pip install httpx   (skipped if it is missing)
"""
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

try:
    from fastapi.testclient import TestClient
    HAVE_CLIENT = True
except Exception:   # httpx missing
    HAVE_CLIENT = False

from src import ingest, translate
from src.pipeline import Vaani

FIXTURES = Path(__file__).parent / "fixtures"


@unittest.skipUnless(HAVE_CLIENT, "httpx not installed")
class TestVoiceApi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import app.api as api
        cls.api = api
        with tempfile.TemporaryDirectory() as tmp:
            chunks = ingest.ingest(FIXTURES, Path(tmp) / "n.csv", Path(tmp) / "c.json")
        api._vaani = Vaani(chunks=chunks, log_unanswered=False)
        cls.client = TestClient(api.app)

    def _fake_models(self, transcript):
        """Pretend speech-to-text returns `transcript`, and text-to-speech writes a tiny file."""
        fake_asr = types.SimpleNamespace(transcribe=lambda path, **kw: transcript)

        def fake_speak(text, out_path, lang="te", slow=True):
            Path(out_path).write_bytes(b"ID3fake")
            return out_path
        fake_tts = types.SimpleNamespace(speak=fake_speak)
        return mock.patch.dict(sys.modules, {"src.asr": fake_asr, "src.tts": fake_tts}), \
            mock.patch("src.asr", fake_asr, create=True), mock.patch("src.tts", fake_tts, create=True)

    def _post_voice(self, transcript, session_id=None):
        patches = self._fake_models(transcript)
        for p in patches:
            p.start()
        try:
            url = "/ask_voice" + (f"?session_id={session_id}" if session_id else "")
            return self.client.post(url, files={"audio": ("q.webm", b"x" * 3000, "audio/webm")})
        finally:
            for p in patches:
                p.stop()

    def test_app_page_and_manifest_are_served(self):
        page = self.client.get("/")
        self.assertEqual(page.status_code, 200)
        self.assertIn("Vaani", page.text)
        self.assertEqual(self.client.get("/manifest.json").status_code, 200)
        self.assertEqual(self.client.get("/icon-192.png").status_code, 200)

    def test_routes_not_hidden_by_page(self):
        data = self.client.get("/health").json()
        self.assertTrue(data["ok"])
        self.assertIn("speech", data)
        self.assertNotIn("key", str(data.values()).replace("SARVAM_API_KEY", ""))

    def test_voice_question_returns_answer_and_audio(self):
        response = self._post_voice("How should I care for the newborn umbilical cord?")
        data = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["status"], "ok")
        self.assertTrue(data["audio_url"])
        self.assertEqual(self.client.get(data["audio_url"]).status_code, 200)

    def test_telugu_question_gets_translated_answer(self):
        with mock.patch.object(translate, "to_telugu", return_value="తెలుగు సమాధానం"):
            data = self._post_voice("బొడ్డు తాడు umbilical cord care గురించి చెప్పండి").json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["language"], "te")
        self.assertIn("తెలుగు సమాధానం", data["answer"])

    def test_telugu_emergency_by_voice(self):
        data = self._post_voice("పాము కరిచింది").json()
        self.assertEqual(data["status"], "emergency")
        self.assertIn("108", data["answer"])

    def test_translation_failure_keeps_english(self):
        with mock.patch.object(translate, "to_telugu", return_value=None):
            data = self._post_voice("బొడ్డు తాడు umbilical cord care గురించి చెప్పండి").json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["language"], "en")

    def test_end_forgets_conversation(self):
        data = self._post_voice("How should I care for the newborn umbilical cord?").json()
        sid = data["session_id"]
        self.assertTrue(self.api.get_vaani().sessions.previous_question(sid))
        self.client.post("/end", json={"session_id": sid})
        self.assertEqual(self.api.get_vaani().sessions.previous_question(sid), "")

    def test_feedback_stats_and_admin(self):
        with tempfile.TemporaryDirectory() as t:
            env = {"VAANI_DB": str(Path(t) / "api.db"), "VAANI_ADMIN_TOKEN": "secret"}
            with mock.patch.dict(os.environ, env):
                self.assertEqual(self.client.post("/feedback", json={
                    "helpful": False, "status": "ok", "question": "q?", "answer": "a."}).json(), {"saved": True})
                self.assertEqual(self.client.get("/stats").json()["not_helpful"], 1)
                self.assertEqual(self.client.get("/admin/unanswered").status_code, 403)
                self.assertEqual(self.client.get("/admin/unanswered", headers={"X-Admin-Token": "wrong"}).status_code, 403)
                ok = self.client.get("/admin/unanswered", headers={"X-Admin-Token": "secret"})
                self.assertEqual(ok.status_code, 200)
                self.assertEqual(ok.json()["not_helpful"][0]["question"], "q?")

    def test_admin_off_without_token(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("VAANI_ADMIN_TOKEN", None)
            self.assertEqual(self.client.get("/admin/unanswered", headers={"X-Admin-Token": "x"}).status_code, 403)

    def test_typed_topic_with_speak_returns_audio(self):
        patches = self._fake_models("")
        for p in patches:
            p.start()
        try:
            data = self.client.post("/ask", json={"text": "How should I care for the newborn umbilical cord?", "speak": True}).json()
        finally:
            for p in patches:
                p.stop()
        self.assertEqual(data["status"], "ok")
        self.assertTrue(data["audio_url"])

    def test_audio_path_tricks_blocked(self):
        self.assertIn(self.client.get("/audio/..%2F..%2Fetc%2Fpasswd").status_code, (404, 422))


class TestTranslateHelper(unittest.TestCase):
    def test_detects_telugu(self):
        self.assertTrue(translate.has_telugu("పాము కరిచింది"))
        self.assertFalse(translate.has_telugu("snake bite"))


if __name__ == "__main__":
    unittest.main()
