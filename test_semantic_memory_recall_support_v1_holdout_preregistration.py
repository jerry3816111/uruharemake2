import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PREREG = ROOT / "configs/semantic_memory_recall_support_v1_holdout_preregistration.json"
DEV_LOCK = ROOT / "configs/semantic_memory_recall_support_v1_development_result_lock.json"


class SemanticMemoryRecallSupportV1HoldoutPreregistrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = json.loads(PREREG.read_text(encoding="utf-8"))

    def test_development_pass_is_locked(self):
        development = json.loads(DEV_LOCK.read_text(encoding="utf-8"))
        self.assertEqual(development["status"], "development_pass_locked")
        self.assertTrue(development["authorization"]["fresh_disjoint_holdout"])

    def test_official_dataset_and_selection_are_frozen(self):
        official = self.payload["official_source"]
        selection = self.payload["frozen_selection"]
        self.assertEqual(official["dataset_rows"], 500)
        self.assertEqual(len(official["dataset_sha256"]), 64)
        self.assertEqual(selection["selected_question_count"], 8)
        self.assertEqual(
            sum(selection["language_assignment_after_hash_sort"].values()),
            8,
        )

    def test_hard_negative_selection_cannot_call_runtime_support(self):
        construction = self.payload["frozen_construction"]
        self.assertTrue(construction["runtime_support_function_forbidden_during_selection"])
        self.assertTrue(construction["manual_case_selection_or_editing_forbidden"])

    def test_target_removal_is_a_strict_safety_gate(self):
        gates = self.payload["holdout_gates"]
        self.assertEqual(gates["row_count_exact"], 32)
        self.assertEqual(gates["wrong_trace_selection_count_max"], 0)
        self.assertEqual(gates["target_removed_selection_count_max"], 0)

    def test_holdout_does_not_pre_authorize_production(self):
        authorization = self.payload["authorization"]
        self.assertFalse(authorization["runtime_change_after_holdout_exposure"])
        self.assertFalse(authorization["production_default_enablement"])
        self.assertFalse(authorization["benchmark_score_claim"])


if __name__ == "__main__":
    unittest.main()
