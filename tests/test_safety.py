"""Run:  py -m unittest discover -s tests -v"""
import unittest

from src import safety


class TestEmergency(unittest.TestCase):
    def test_english_emergencies(self):
        for text in ["my father has chest pain", "she is bleeding a lot",
                     "he is having fits", "snake bite in the field", "he cannot breathe",
                     "A snake bit my brother in the field"]:
            self.assertEqual(safety.check_emergency(text), "emergency", text)

    def test_telugu_emergencies(self):
        for text in ["మా అమ్మకు ఛాతీ నొప్పి వస్తోంది", "పాము కరిచింది", "పిల్లవాడికి ఫిట్స్ వస్తున్నాయి"]:
            self.assertEqual(safety.check_emergency(text), "emergency", text)

    def test_crisis(self):
        self.assertEqual(safety.check_emergency("I want to die"), "crisis")

    def test_reduced_fetal_movement(self):
        # Found by the 150-question eval: "baby not moving" missed this wording.
        for text in ["The baby is not moving inside my womb", "my baby has stopped moving",
                     "కడుపులో బిడ్డ కదలడం లేదు"]:
            self.assertEqual(safety.check_emergency(text), "emergency", text)

    def test_no_false_alarm_on_benefits(self):
        # 'fits' must not match inside 'benefits'
        self.assertIsNone(safety.check_emergency("what are the benefits of breastfeeding"))

    def test_normal_question(self):
        self.assertIsNone(safety.check_emergency("how to prevent diarrhoea"))


class TestDose(unittest.TestCase):
    def test_dose_requests(self):
        for text in ["what is the dose of paracetamol", "how many tablets for fever", "మందు మోతాదు ఎంత"]:
            self.assertTrue(safety.is_dose_request(text), text)

    def test_insulin_and_units(self):
        # Found by the 150-question eval.
        for text in ["How much insulin should I take?", "how many units of insulin"]:
            self.assertTrue(safety.is_dose_request(text), text)

    def test_normal_not_dose(self):
        self.assertFalse(safety.is_dose_request("how to care for a newborn"))
        # Water / ORS amounts are home care, not medicine doses.
        self.assertFalse(safety.is_dose_request("How much water should a child drink?"))


class TestAnswerFilter(unittest.TestCase):
    def test_removes_dose_sentence(self):
        safe, removed = safety.filter_answer("Keep drinking fluids. Take paracetamol 500 mg twice a day.")
        self.assertEqual(safe, "Keep drinking fluids.")
        self.assertEqual(removed, 1)

    def test_removes_diagnosis_sentence(self):
        safe, removed = safety.filter_answer("You have malaria. Rest well.")
        self.assertEqual(safe, "Rest well.")

    def test_keeps_ors_water_amounts(self):
        safe, removed = safety.filter_answer("Give 200 ml of ORS after each loose motion.")
        self.assertEqual(removed, 0)


if __name__ == "__main__":
    unittest.main()
