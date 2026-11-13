"""PDF text cleaning and whole-sentence answers (bugs found in the UI review, 2026-11-13)."""
import unittest

from src.answer import pick_sentences
from src.ingest import clean_text


class TestCleanText(unittest.TestCase):
    def test_symbol_font_bullets_removed(self):
        # U+F0B7 / U+F06C showed as a box on screen and were read aloud by speech.
        self.assertEqual(clean_text("cases  During house visits"), "cases. During house visits")
        self.assertEqual(clean_text("Signs:  fever  rash"), "Signs: fever. rash")

    def test_normal_bullets_become_sentences(self):
        self.assertEqual(clean_text("Done. ● Next item • Last"), "Done. Next item. Last")

    def test_ligatures_and_dot_leaders(self):
        self.assertEqual(clean_text("ﬁrst aid"), "first aid")
        self.assertEqual(clean_text("Contents……… 12 Introduction"), "Contents 12 Introduction")

    def test_broken_words_joined(self):
        self.assertEqual(clean_text("treat-\nment works"), "treatment works")


class TestWholeSentences(unittest.TestCase):
    HIT = {"text": "cases in the village are common. Wash the wound with soap and water for "
                   "fifteen minutes. Go to the health centre for the rabies vaccine quickly.",
           "score": 0.9}

    def test_skips_half_sentence_at_chunk_start(self):
        answer = pick_sentences("How do I wash a dog bite wound with soap?", [self.HIT])
        self.assertTrue(answer.startswith("Wash the wound"), answer)
        self.assertNotIn("cases in the village", answer)

    def test_telugu_question_uses_english_search_text(self):
        hit = dict(self.HIT, search_text="How should I wash a dog bite wound? (dog bite rabies; soap)")
        answer = pick_sentences("కుక్క కాటు గాయాన్ని ఎలా కడగాలి?", [hit])
        self.assertIn("Wash the wound", answer)


if __name__ == "__main__":
    unittest.main()
