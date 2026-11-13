"""Glossary part of Telugu -> English search text. No models needed (NLLB switched off)."""
import os
import unittest
from unittest import mock

from src import query_translate as qt


class TestGlossary(unittest.TestCase):
    def test_fixes_known_mistranslations(self):
        # NLLB said "snowman", "hopeful worker" and "abdominal cord" for these.
        self.assertIn("heatstroke", qt.glossary_terms("వడదెబ్బ అంటే ఏమిటి?"))
        self.assertIn("ASHA worker", qt.glossary_terms("ఆశా కార్యకర్త ఏం సహాయం చేస్తుంది?"))
        self.assertIn("umbilical cord", qt.glossary_terms("బొడ్డు తాడును ఎలా శుభ్రంగా ఉంచాలి?"))

    def test_no_repeats(self):
        terms = qt.glossary_terms("కుక్క కాటు కుక్క కరిస్తే")
        self.assertEqual(len(terms), len(set(terms)))

    def test_english_question_is_left_alone(self):
        self.assertIsNone(qt.to_english("What are the symptoms of dengue?"))

    def test_glossary_works_without_the_model(self):
        with mock.patch.dict(os.environ, {"VAANI_NO_NLLB": "1"}):
            qt.machine_translate.cache_clear()
            self.assertEqual(qt.to_english("డెంగ్యూ లక్షణాలు ఏమిటి?"), "(dengue)")
            self.assertIsNone(qt.to_english("ఏమిటి?"))   # Telugu, but nothing known


if __name__ == "__main__":
    unittest.main()
