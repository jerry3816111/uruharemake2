import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent


class CognitivePlanDecompositionV66ResultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = json.loads(
            (ROOT / "reports/cognitive_plan_decomposition_v66_raw.json").read_text(encoding="utf-8")
        )
        cls.analysis = json.loads(
            (ROOT / "reports/cognitive_plan_decomposition_v66_analysis.json").read_text(encoding="utf-8")
        )

    def test_formal_run_integrity_is_complete(self):
        self.assertEqual(self.raw["warmup_transport_attempt_count"], 5)
        self.assertEqual(self.raw["scored_case_count"], 36)
        self.assertEqual(self.raw["scored_transport_attempt_count"], 60)
        self.assertEqual(self.raw["transport_attempt_count"], 65)
        self.assertEqual(self.raw["transport_error_count"], 0)
        self.assertTrue(self.raw["preflight"]["passed"])
        self.assertFalse(self.raw["gold_in_raw"])
        self.assertFalse(self.raw["production_runtime_changed"])
        self.assertFalse(self.raw["production_memory_read_or_write"])
        self.assertTrue(self.analysis["run_integrity"]["passed"])

    def test_fixed_decomposition_has_no_exact_case_gain(self):
        metrics = self.analysis["metrics"]
        control = metrics["two_pass_full_plan_control"]
        treatment = metrics["two_stage_responsibility_decomposition"]
        self.assertEqual(control["exact_case_count"], 5)
        self.assertEqual(treatment["exact_case_count"], 5)
        self.assertEqual(treatment["exact_field_hits"], 83)
        self.assertEqual(control["exact_field_hits"], 80)
        pair = self.analysis["pairwise"]["treatment_vs_matched_control"]
        self.assertEqual(pair["newly_correct"], 3)
        self.assertEqual(pair["regressions"], 3)
        self.assertFalse(pair["eligible"])

    def test_decomposition_is_faster_but_not_accurate_enough(self):
        metrics = self.analysis["metrics"]
        control = metrics["two_pass_full_plan_control"]
        treatment = metrics["two_stage_responsibility_decomposition"]
        self.assertLess(
            treatment["latency_median_seconds_per_case"],
            control["latency_median_seconds_per_case"],
        )
        self.assertEqual(treatment["all_required_tools_parse_count"], 12)
        self.assertLess(treatment["exact_case_accuracy"], 0.6667)
        self.assertEqual(
            self.analysis["decision"],
            "freeze_result_and_stop_fixed_two_stage_decomposition_as_sufficient_solution",
        )

    def test_result_lock_forbids_production_change(self):
        lock_path = ROOT / "configs/cognitive_plan_decomposition_v66_result_lock.json"
        self.assertTrue(lock_path.exists())
        lock = json.loads(lock_path.read_text(encoding="utf-8"))
        for name, artifact in lock["frozen_artifacts"].items():
            digest = hashlib.sha256((ROOT / artifact["path"]).read_bytes()).hexdigest()
            self.assertEqual(digest, artifact["sha256"], name)
        self.assertFalse(lock["authorizations"]["fixed_two_stage_production_change"])
        self.assertFalse(lock["authorizations"]["adaptive_router_from_current_families"])
        self.assertFalse(lock["authorizations"]["production_runtime_change"])


if __name__ == "__main__":
    unittest.main()
