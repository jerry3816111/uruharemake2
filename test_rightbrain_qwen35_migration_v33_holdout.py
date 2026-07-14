import json
import unittest
from pathlib import Path

from build_rightbrain_qwen35_migration_v33_holdout import build_dataset


ROOT = Path(__file__).resolve().parent
DATASET_PATH = ROOT / "datasets" / "rightbrain_qwen35_migration_v33_holdout.json"


class RightBrainQwen35MigrationV33HoldoutTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.generated = build_dataset()
        cls.frozen = json.loads(DATASET_PATH.read_text(encoding="utf-8"))

    def test_generated_dataset_matches_frozen_file(self):
        self.assertEqual(self.generated, self.frozen)

    def test_preregistered_case_accounting(self):
        self.assertEqual(len(self.frozen["rightbrain_cases"]), 48)
        self.assertEqual(len(self.frozen["action_cases"]), 120)
        self.assertEqual(set(self.frozen["accounting"]["rightbrain_categories"].values()), {4})
        self.assertEqual(set(self.frozen["accounting"]["action_families"].values()), {20})

    def test_no_formal_calls_precede_holdout(self):
        separation = self.frozen["source_separation"]
        self.assertEqual(separation["formal_model_calls_before_this_dataset_commit"], 0)
        self.assertEqual(separation["exact_input_overlap_with_v21_v29_and_promotion_holdout"], 0)
        self.assertFalse(separation["informal_screening_reuse_allowed"])

    def test_private_memory_cases_have_forbidden_terms(self):
        private_cases = [case for case in self.frozen["rightbrain_cases"] if case["category"] == "private_memory_suppression"]
        self.assertEqual(len(private_cases), 4)
        self.assertTrue(all(case["forbidden_substrings"] for case in private_cases))
        self.assertTrue(all(not case["logic"]["memory_use_expected"] for case in private_cases))

    def test_negated_actions_freeze_forbidden_calls(self):
        negated = [case for case in self.frozen["action_cases"] if case["family"] == "negated_action"]
        self.assertEqual(len(negated), 20)
        self.assertTrue(all(case["forbidden_calls"] for case in negated))


if __name__ == "__main__":
    unittest.main()
