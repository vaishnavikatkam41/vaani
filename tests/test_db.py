"""Tests the small database. Run:  py -m unittest discover -s tests -t . -v"""
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from src import db, ingest
from src.pipeline import Vaani

FIXTURES = Path(__file__).parent / "fixtures"


class TestDb(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "test.db"

    def tearDown(self):
        self.tmp.cleanup()

    def test_unanswered_is_saved(self):
        db.log_unanswered("Which crop is best?", db_path=self.path)
        rows = db.list_unanswered(db_path=self.path)
        self.assertEqual(rows[0]["question"], "Which crop is best?")

    def test_thumbs_up_saves_no_text(self):
        db.add_feedback(True, "ok", "sure", 0.9, question="private words", answer="x",
                        db_path=self.path)
        conn = sqlite3.connect(self.path)
        try:
            row = conn.execute("SELECT question, answer FROM feedback").fetchone()
        finally:
            conn.close()   # Windows cannot delete a file that is still open
        self.assertEqual(row, (None, None))

    def test_thumbs_down_saves_text_for_review(self):
        db.add_feedback(False, "ok", "unsure", 0.2, question="q?", answer="a.",
                        sources=["WHO guide, page 1"], db_path=self.path)
        rows = db.list_not_helpful(db_path=self.path)
        self.assertEqual(rows[0]["question"], "q?")
        self.assertEqual(rows[0]["sources"], "WHO guide, page 1")

    def test_stats_are_counts_only(self):
        db.log_unanswered("a", db_path=self.path)
        db.add_feedback(True, db_path=self.path)
        db.add_feedback(False, question="b", db_path=self.path)
        self.assertEqual(db.stats(self.path),
                         {"unanswered": 1, "feedback": 2, "helpful": 1, "not_helpful": 1})

    def test_pipeline_logs_idk_to_database(self):
        with tempfile.TemporaryDirectory() as t:
            chunks = ingest.ingest(FIXTURES, Path(t) / "n.csv", Path(t) / "c.json",
                                   cache_dir=Path(t) / "cache")
        with mock.patch.dict(os.environ, {"VAANI_DB": str(self.path)}):
            Vaani(chunks=chunks).ask("Which crop is best for black soil?")
        self.assertEqual(len(db.list_unanswered(db_path=self.path)), 1)


if __name__ == "__main__":
    unittest.main()
