import json
import unittest
from pathlib import Path

import analyze_semantic_memory_recall_support_v1_holdout as analysis


ROOT = Path(__file__).resolve().parent


class AnalyzeSemanticMemoryRecallSupportV1HoldoutTests(unittest.TestCase):
    def test_locked_failure_has_expected_general_diagnosis(self):
        payload = analysis.diagnose(
            json.loads(
                (ROOT / "configs/semantic_memory_recall_support_v1_holdout_cases.json").read_text(
                    encoding="utf-8"
                )
            ),
            json.loads(
                (ROOT / "configs/semantic_memory_recall_support_v1_holdout_evaluation_contract.json").read_text(
                    encoding="utf-8"
                )
            ),
            json.loads(
                (ROOT / "reports/semantic_memory_recall_support_v1_holdout.json").read_text(
                    encoding="utf-8"
                )
            ),
        )

        observed = payload["observed"]
        self.assertEqual(observed["target_removed_selection_count"], 6)
        self.assertEqual(observed["target_lexically_supported_count"], 7)
        self.assertEqual(observed["replacement_lexically_supported_count"], 3)
        self.assertEqual(observed["hard_negative_lexically_supported_count"], 6)
        self.assertEqual(observed["target_shared_count_range"], [0, 4])
        self.assertEqual(observed["hard_negative_shared_count_range"], [0, 4])
        self.assertEqual(observed["whole_record_sensitive_suppression_count"], 1)
        self.assertFalse(
            payload["threshold_conclusion"][
                "shared_count_threshold_can_separate_targets_and_negatives"
            ]
        )


if __name__ == "__main__":
    unittest.main()
