import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent


class ProfileAnswerGeneralizationV70ResultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = json.loads(
            (ROOT / "reports/profile_answer_generalization_v70_raw.json").read_text(
                encoding="utf-8"
            )
        )
        cls.analysis = json.loads(
            (ROOT / "reports/profile_answer_generalization_v70_analysis.json").read_text(
                encoding="utf-8"
            )
        )
        cls.lock = json.loads(
            (
                ROOT / "configs/profile_answer_generalization_v70_result_lock.json"
            ).read_text(encoding="utf-8")
        )

    def test_formal_run_is_complete_and_gold_blind(self):
        self.assertTrue(self.analysis["run_integrity"]["passed"])
        self.assertEqual(self.raw["row_count"], 72)
        self.assertEqual(
            len({(row["case_id"], row["condition"]) for row in self.raw["rows"]}),
            72,
        )
        self.assertFalse(self.raw["gold_in_raw"])
        self.assertTrue(self.raw["locked_preflight"]["passed"])
        self.assertEqual(self.raw["locked_preflight"]["observed_test_count"], 15)
        self.assertTrue(all(row["temporary_database"] for row in self.raw["rows"]))

    def test_typed_active_projection_does_not_beat_matched_append_only(self):
        append_only = self.analysis["metrics"][
            "matched_append_only_projection_control"
        ]
        treatment = self.analysis["metrics"]["typed_active_projection_treatment"]
        self.assertEqual(append_only["overall_pass_count"], 11)
        self.assertEqual(treatment["overall_pass_count"], 10)
        self.assertEqual(treatment["relevant_pass_count"], 8)
        self.assertEqual(treatment["irrelevant_profile_intrusion_count"], 5)
        self.assertEqual(treatment["abstention_pass_count"], 0)
        self.assertEqual(
            self.analysis["pairwise"]["newly_passed_vs_append_only"], 0
        )
        self.assertEqual(self.analysis["pairwise"]["regressions_vs_append_only"], 1)

    def test_failed_gates_keep_profile_out_of_answers(self):
        self.assertEqual(
            self.analysis["decision"], "freeze_and_keep_profile_out_of_answers"
        )
        self.assertFalse(self.analysis["success_gates"]["passed"])
        self.assertFalse(self.lock["answer_path_shadow_authorized"])
        self.assertFalse(self.lock["runtime_activation_authorized"])
        self.assertFalse(self.lock["post_run_case_editing_authorized"])
        self.assertFalse(self.lock["post_run_threshold_change_authorized"])

    def test_result_lock_binds_every_formal_artifact(self):
        for name, artifact in self.lock["frozen_artifacts"].items():
            actual = hashlib.sha256((ROOT / artifact["path"]).read_bytes()).hexdigest()
            self.assertEqual(actual, artifact["sha256"], name)


if __name__ == "__main__":
    unittest.main()
