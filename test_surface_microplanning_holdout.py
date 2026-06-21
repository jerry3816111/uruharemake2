import json
import os
import unittest
from pathlib import Path

from eval_surface_microplanning_holdout import _evaluate_case, _summarize
from project_paths import SURFACE_MICROPLANNING_HOLDOUT_DATASET_PATH
from uruha_brain_mac import LeftBrain


class SurfaceMicroplanningHoldoutTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(SURFACE_MICROPLANNING_HOLDOUT_DATASET_PATH, "r", encoding="utf-8") as handle:
            cls.dataset = json.load(handle)
        left = LeftBrain(None)
        cls.rows = [_evaluate_case(left, case) for case in cls.dataset["cases"]]
        cls.summary = _summarize(cls.rows)

    def test_dataset_is_evaluation_only(self):
        self.assertEqual(self.dataset["scope"], "developer_visible_technical_generalization_set")
        self.assertIn("never loaded", self.dataset["runtime_isolation"])
        base_dir = os.path.dirname(SURFACE_MICROPLANNING_HOLDOUT_DATASET_PATH)
        project_dir = os.path.dirname(base_dir)
        for filename in ("uruha_brain_mac.py", "uruha_leftbrain_rules.py", "uruha_runtime.py"):
            with self.subTest(filename=filename):
                source = Path(project_dir, filename).read_text(encoding="utf-8")
                self.assertNotIn("surface_microplanning_holdout.json", source)

    def test_all_technical_contracts_pass(self):
        failed = [row["id"] for row in self.rows if not row["pass"]]
        self.assertEqual(failed, [])
        self.assertEqual(self.summary["case_pass_rate"], 1.0)
        self.assertEqual(self.summary["risk_calibration_rate"], 1.0)
        self.assertEqual(self.summary["speech_move_contract_rate"], 1.0)
        self.assertEqual(self.summary["benign_false_alarm_rate"], 0.0)
        self.assertEqual(self.summary["forbidden_overreaction_rate"], 0.0)

    def test_outputs_are_not_exact_template_duplicates(self):
        self.assertEqual(self.summary["exact_reply_unique_ratio"], 1.0)

    def test_planner_semantic_groups_survive_surface_realization(self):
        failed = [
            row["id"]
            for row in self.rows
            if row["planner_semantic_group_hits"] and not all(row["planner_semantic_group_hits"])
        ]
        self.assertEqual(failed, [])

    def test_report_scope_does_not_claim_human_naturalness(self):
        self.assertIn("cannot establish human naturalness", self.dataset["research_boundary"])


if __name__ == "__main__":
    unittest.main()
