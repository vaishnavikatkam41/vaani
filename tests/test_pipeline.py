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
        # We watch which text is sent to the search. This does not depend on the
        # "I don't know" limit, so the test stays correct when you tune that limit.
        seen = []
        original = self.vaani.retriever.search

        def spy(query, k=3):
            seen.append(query)
            return original(query, k=k)

        self.vaani.retriever.search = spy
        try:
            result = self.vaani.ask("when to go to hospital", session_id=sid)
            self.vaani.ask("when to go to hospital")          # no session: no memory
        finally:
            del self.vaani.retriever.search                    # put the real search back
        self.assertIn("umbilical cord", seen[0])               # memory joined the old question
        self.assertEqual(seen[1], "when to go to hospital")    # without memory: unchanged
        self.assertEqual(result["status"], "ok")
        self.vaani.end(sid)
        self.assertEqual(self.vaani.sessions.previous_question(sid), "")


if __name__ == "__main__":
    unittest.main()
