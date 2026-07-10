import json
import tempfile
import unittest
from pathlib import Path

from eval_rightbrain_selector_human_preference_v1 import build_report, write_markdown
from eval_rightbrain_repair_selector_v1 import build_evaluation_report
from import_human_blind_evidence import load_blind_evidence
from project_paths import (
    RIGHTBRAIN_REPAIR_SELECTION_V1_DATASET_PATH,
    RIGHTBRAIN_REPAIR_SELECTOR_V1_MODEL_PATH,
)
from rightbrain_repair_selector import load_model_artifact


class RightBrainSelectorHumanPreferenceV1Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        blind_rows, _, source_summaries = load_blind_evidence()
        selection_rows = json.loads(
            Path(RIGHTBRAIN_REPAIR_SELECTION_V1_DATASET_PATH).read_text(encoding="utf-8")
        )
        model = load_model_artifact(RIGHTBRAIN_REPAIR_SELECTOR_V1_MODEL_PATH)
        cls.report = build_report(blind_rows, source_summaries, selection_rows, model)
        cls.selection_rows = selection_rows
        cls.model = model

    def test_strict_subset_removes_all_exact_selector_training_text_overlap(self):
        self.assertEqual(self.report["data"]["completed_task_count"], 19)
        self.assertEqual(self.report["data"]["completed_candidate_count"], 76)
        self.assertEqual(self.report["data"]["strict_task_count"], 12)
        self.assertEqual(self.report["data"]["strict_candidate_count"], 48)
        self.assertTrue(self.report["gate"]["strict_candidate_text_overlap_is_zero"])

    def test_existing_learned_selector_is_not_promoted_on_human_preference(self):
        strict = self.report["strict_no_exact_text_overlap"]["strategies"]
        learned = strict["learned_selector_v1"]
        heuristic = strict["current_runtime_heuristic_proxy"]

        self.assertLess(
            learned["selected_mean_naturalness_1_5"],
            heuristic["selected_mean_naturalness_1_5"],
        )
        self.assertFalse(self.report["takeover_recommended"])

    def test_human_oracle_is_an_explicit_upper_bound(self):
        oracle = self.report["strict_no_exact_text_overlap"]["strategies"]["human_score_oracle"]
        self.assertEqual(oracle["top_score_hit_rate"], 1.0)

    def test_report_documents_single_rater_boundary(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "report.md"
            write_markdown(self.report, output)
            text = output.read_text(encoding="utf-8")
        self.assertIn("單一評分者", text)
        self.assertIn("observe-only", self.report["decision_zh"])

    def test_human_preference_failure_blocks_synthetic_selector_promotion(self):
        combined = build_evaluation_report(
            self.selection_rows,
            self.model,
            human_preference_report=self.report,
        )

        self.assertTrue(combined["synthetic_contract_gate_passed"])
        self.assertFalse(combined["gate"]["human_preference_takeover_recommended"])
        self.assertFalse(combined["gate_passed"])


if __name__ == "__main__":
    unittest.main()
