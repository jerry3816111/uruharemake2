import json
import unittest
from pathlib import Path

from eval_rightbrain_selector_runtime_soak_v1 import build_runtime_soak_report
from project_paths import RIGHTBRAIN_REPAIR_SELECTION_V1_DATASET_PATH


class RightBrainSelectorRuntimeSoakTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rows = json.loads(Path(RIGHTBRAIN_REPAIR_SELECTION_V1_DATASET_PATH).read_text(encoding="utf-8"))
        cls.report = build_runtime_soak_report(rows)

    def test_full_runtime_soak_passes(self):
        self.assertTrue(self.report["gate_passed"], msg=self.report["gate"])
        self.assertEqual(self.report["summary"]["case_count"], 360)
        self.assertEqual(self.report["summary"]["rejected_candidate_count"], 2873)
        self.assertEqual(self.report["failures"], [])

    def test_contract_disjoint_test_split_is_primary_gate(self):
        split = self.report["split"]
        self.assertEqual(split["row_counts"], {"train": 252, "validation": 54, "test": 54})
        self.assertEqual(
            split["fingerprint_overlap_counts"],
            {"train_validation": 0, "train_test": 0, "validation_test": 0},
        )
        test = self.report["split_metrics"]["test"]
        self.assertEqual(test["case_count"], 54)
        self.assertEqual(test["learned_gold_selection_rate"], 1.0)

    def test_runtime_gate_detects_every_corrupted_candidate(self):
        summary = self.report["summary"]
        self.assertEqual(summary["runtime_detected_rejected_candidate_count"], 2873)
        self.assertEqual(summary["runtime_rejected_candidate_detection_rate"], 1.0)
        self.assertEqual(self.report["runtime_missed_source_counts"], {})

    def test_shadow_never_changes_visible_output_or_selects_rejected(self):
        summary = self.report["summary"]
        self.assertEqual(summary["visible_output_unchanged_rate"], 1.0)
        self.assertEqual(summary["learned_gate_rejected_selection_count"], 0)
        self.assertEqual(summary["learned_strict_valid_rate"], 1.0)


if __name__ == "__main__":
    unittest.main()
