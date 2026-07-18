import hashlib
import json
import unittest
from pathlib import Path

from run_profile_grounded_speech_plan_v72 import CONDITIONS


ROOT = Path(__file__).resolve().parent
RAW = ROOT / "reports/profile_grounded_speech_plan_v72_raw.json"
ANALYSIS = ROOT / "reports/profile_grounded_speech_plan_v72_analysis.json"
RESULT = ROOT / "configs/profile_grounded_speech_plan_v72_result_lock.json"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ProfileGroundedSpeechPlanV72ResultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = load(RAW)
        cls.analysis = load(ANALYSIS)
        cls.result = load(RESULT)

    def test_result_lock_binds_every_formal_artifact(self):
        for artifact in self.result["frozen_artifacts"].values():
            path = ROOT / artifact["path"]
            self.assertTrue(path.exists())
            self.assertEqual(sha(path), artifact["sha256"])

    def test_formal_run_integrity_is_exact_and_gold_free(self):
        self.assertEqual(self.raw["git_head"], "81139cb542877100e3fb6b50e84ccd03930ef603")
        self.assertEqual(self.raw["row_count"], 72)
        self.assertEqual(self.raw["selector_call_count"], 24)
        self.assertEqual(self.raw["locked_preflight"]["observed_test_count"], 39)
        self.assertTrue(self.raw["locked_preflight"]["passed"])
        self.assertFalse(self.raw["gold_in_raw"])
        self.assertTrue(all("expected" not in row and "gold" not in row for row in self.raw["rows"]))
        self.assertTrue(self.analysis["run_integrity"]["passed"])

    def test_ability_passes_with_relation_attribution(self):
        current = self.analysis["metrics"][CONDITIONS[0]]
        value_only = self.analysis["metrics"][CONDITIONS[1]]
        treatment = self.analysis["metrics"][CONDITIONS[2]]
        self.assertEqual((current["overall_case_pass_count"], current["relevant_case_pass_count"]), (11, 3))
        self.assertEqual((value_only["overall_case_pass_count"], value_only["relevant_case_pass_count"]), (12, 4))
        self.assertEqual((treatment["overall_case_pass_count"], treatment["relevant_case_pass_count"]), (24, 16))
        self.assertEqual(treatment["value_slot_hit_count"], 16)
        self.assertEqual(treatment["relation_slot_hit_count"], 12)
        self.assertEqual(treatment["polarity_error_count"], 0)
        self.assertEqual(treatment["structural_label_leak_count"], 0)
        self.assertEqual(treatment["irrelevant_profile_intrusion_count"], 0)
        self.assertEqual(treatment["abstention_pass_count"], 4)
        self.assertEqual(
            self.analysis["pairwise"],
            {
                "newly_passed_vs_value_only": 12,
                "regressions_vs_value_only": 0,
                "newly_passed_vs_current_pipeline": 13,
            },
        )
        self.assertTrue(self.analysis["ability_gates"]["passed"])

    def test_cost_failure_and_no_activation_are_preserved(self):
        self.assertEqual(self.analysis["cost"]["leftbrain_model_calls_reduction_vs_current"], 6)
        self.assertFalse(self.analysis["cost_gates"]["checks"]["leftbrain_calls"])
        self.assertFalse(self.analysis["cost_gates"]["passed"])
        self.assertEqual(self.analysis["decision"], "authorize_cost_optimization_research_only")
        self.assertEqual(self.result["decision"], "authorize_cost_optimization_research_only")
        self.assertFalse(self.result["grounded_plan_shadow_authorized"])
        self.assertFalse(self.result["runtime_activation_authorized"])
        self.assertFalse(self.result["post_run_case_editing_authorized"])
        self.assertFalse(self.result["post_run_threshold_change_authorized"])


if __name__ == "__main__":
    unittest.main()
