import json
import unittest
from pathlib import Path

from uruha_brain_mac import MemoryManager
from uruha_profile_assertion import classify_profile_assertion_scope


ROOT = Path(__file__).resolve().parent


class ProfileAssertionMultilingualBoundaryRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.memory = object.__new__(MemoryManager)

    def test_japanese_lexical_overlap_is_not_mistaken_for_chinese_reporting(self):
        direct_assertions = {
            "写真が好き。": [("like", "写真")],
            "写経が好き。": [("like", "写経")],
            "質問が好き。": [("like", "質問")],
            "訪問着が好き。": [("like", "訪問着")],
        }
        for utterance, expected in direct_assertions.items():
            with self.subTest(utterance=utterance):
                self.assertEqual(self.memory._extract_profile_facts(utterance), expected)

    def test_chinese_reporting_constructions_remain_blocked(self):
        reports = (
            "朋友說我喜歡露營。",
            "朋友寫：我喜歡露營。",
            "朋友問我喜歡露營。",
            "朋友表示我喜歡露營。",
            "朋友提到我喜歡露營。",
        )
        for utterance in reports:
            with self.subTest(utterance=utterance):
                extracted = [("like", "露營")]
                decision = classify_profile_assertion_scope(utterance, extracted)
                self.assertFalse(decision["allow"])
                self.assertEqual(decision["reason"], "reported_scope")

    def test_frozen_v68_cases_do_not_regress(self):
        dataset = json.loads(
            (ROOT / "datasets/profile_assertion_boundary_v68.json").read_text(encoding="utf-8")
        )
        for case in dataset["cases"]:
            with self.subTest(case_id=case["id"]):
                observed = [
                    {"fact_type": fact_type, "value": value}
                    for fact_type, value in self.memory._extract_profile_facts(case["utterance"])
                ]
                self.assertEqual(observed, case["expected_facts"])

    def test_v69_preflight_now_has_all_expected_writes(self):
        dataset = json.loads(
            (ROOT / "datasets/profile_state_transition_v69.json").read_text(encoding="utf-8")
        )
        observed_ids = []
        expected_ids = []
        for case in dataset["cases"]:
            expected_ids.extend(case["expected"]["written_turn_ids"])
            for turn in case["turns"]:
                facts = self.memory._extract_profile_facts(turn["utterance"])
                if facts:
                    observed_ids.append(turn["turn_id"])
        self.assertEqual(observed_ids, expected_ids)
        self.assertEqual(len(observed_ids), 33)


if __name__ == "__main__":
    unittest.main()
