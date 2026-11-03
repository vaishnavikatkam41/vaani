"""Tests the full brain on a small fake document (tests/fixtures).
Run:  py -m unittest discover -s tests -v
"""
import tempfile
import unittest
from pathlib import Path

from src import ingest
from src.pipeline import Vaani

FIXTURES = Path(__file__).parent / "fixtures"


class TestPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with tempfile.TemporaryDirectory() as tmp:
            chunks = ingest.ingest(FIXTURES, Path(tmp) / "none.csv", Path(tmp) / "chunks.json")
        cls.vaani = Vaani(chunks=chunks, log_unanswered=False)

    def test_ingest_made_chunks(self):
        self.assertGreater(len(self.vaani.retriever.chunks), 0)

    def test_normal_question_gets_answer_with_source(self):
        result = self.vaani.ask("How do I give fluids to a child with loose motions?")
        self.assertEqual(result["status"], "ok")
        self.assertIn("ORS", result["answer"])
        self.assertTrue(result["sources"])

    def test_emergency_skips_search(self):
        result = self.vaani.ask("my child is having fits")
        self.assertEqual(result["status"], "emergency")
        self.assertIn("108", result["answer"])

    def test_out_of_scope_says_idk(self):
        result = self.vaani.ask("Which crop is best for black soil?")
        self.assertEqual(result["status"], "idk")

    def test_dose_request_refused(self):
        result = self.vaani.ask("What is the dose of paracetamol for my child?")
        self.assertEqual(result["status"], "refuse")

    def test_answer_never_contains_a_dose(self):
        result = self.vaani.ask("Should zinc be given for diarrhoea?")
        self.assertNotIn("mg", result["answer"])

    def test_follow_up_uses_previous_question(self):
        sid = "test-session"
        self.vaani.ask("How should I care for the newborn umbilical cord?", session_id=sid)
        # Alone, this short question has no topic. With the memory, it means "cord".
        alone = self.vaani.ask("when to go to health centre")
        self.assertEqual(alone["status"], "idk")
        result = self.vaani.ask("when to go to hospital", session_id=sid)
        self.assertEqual(result["status"], "ok")
        self.vaani.end(sid)
        self.assertEqual(self.vaani.sessions.previous_question(sid), "")


if __name__ == "__main__":
    unittest.main()
