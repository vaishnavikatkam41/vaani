"""Safety checks over the whole evaluation question bank (data/test_questions.csv).

These need no PDFs and no models, so they run in CI on every push.
If someone adds an emergency question that the safety layer misses, CI fails.
"""
import csv
import unittest

from src import config, safety


def load(kind):
    with open(config.TEST_QUESTIONS, newline="", encoding="utf-8") as f:
        return [r for r in csv.DictReader(f) if r["type"] == kind]


class TestQuestionBank(unittest.TestCase):
    def test_bank_is_big_enough(self):
        with open(config.TEST_QUESTIONS, newline="", encoding="utf-8") as f:
            self.assertGreaterEqual(sum(1 for _ in csv.DictReader(f)), 140)

    def test_every_emergency_is_caught(self):
        for row in load("emergency"):
            want = "crisis" if row.get("topic") == "crisis" else "emergency"
            self.assertEqual(safety.check_emergency(row["question"]), want, row["question"])

    def test_every_dose_request_is_refused(self):
        for row in load("dose_request"):
            self.assertTrue(safety.is_dose_request(row["question"]), row["question"])

    def test_normal_questions_are_not_blocked(self):
        # Normal health questions must reach the search step (no false alarms).
        for row in load("normal"):
            self.assertIsNone(safety.check_emergency(row["question"]), row["question"])
            self.assertFalse(safety.is_dose_request(row["question"]), row["question"])


if __name__ == "__main__":
    unittest.main()
