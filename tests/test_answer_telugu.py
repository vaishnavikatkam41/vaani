"""A Telugu question shares no words with English sources. It must still get the best passage."""
import unittest

from src import answer


class TestTeluguFallback(unittest.TestCase):
    def test_no_shared_words_uses_best_passage(self):
        hits = [{"text": "Give the child extra fluids at home. Continue breastfeeding during fever. "
                         "Visit the health centre if the fever lasts more than three days.",
                 "source_name": "WHO guide", "page": 1, "score": 0.83}]
        text = answer.pick_sentences("పిల్లలకు జ్వరం వస్తే ఏం చేయాలి?", hits)
        self.assertIn("extra fluids", text)

    def test_english_question_still_picks_matching_sentences(self):
        hits = [{"text": "Wash your hands with soap. Give the child extra fluids at home during fever.",
                 "source_name": "WHO guide", "page": 1, "score": 0.9}]
        text = answer.pick_sentences("fever fluids", hits)
        self.assertIn("fluids", text)
        self.assertNotIn("Wash", text)


if __name__ == "__main__":
    unittest.main()
