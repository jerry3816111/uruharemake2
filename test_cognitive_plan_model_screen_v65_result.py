import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent


class CognitivePlanModelScreenV65ResultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = json.loads(
            (ROOT / "reports/cognitive_plan_model_screen_v65_raw.json").read_text(encoding="utf-8")
        )
        cls.analysis = json.loads(
            (ROOT / "reports/cognitive_plan_model_screen_v65_analysis.json").read_text(encoding="utf-8")
        )

    def test_formal_run_integrity_is_complete(self):
        self.assertEqual(self.raw["warmup_call_count"], 3)
        self.assertEqual(self.raw["scored_model_call_count"], 36)
        self.assertEqual(self.raw["transport_attempt_count"], 39)
        self.assertEqual(self.raw["transport_error_count"], 0)
        self.assertEqual(len(self.raw["rows"]), 36)
        self.assertTrue(self.raw["preflight"]["passed"])
        self.assertFalse(self.raw["gold_in_raw"])
        self.assertFalse(self.raw["production_runtime_changed"])
        self.assertFalse(self.raw["production_memory_read_or_write"])

    def test_frozen_decision_rejects_all_candidates(self):
        self.assertEqual(
            self.analysis["decision"],
            "freeze_negative_result_and_stop_one_call_model_replacement",
        )
        self.assertIsNone(self.analysis["selected_candidate"])
        self.assertTrue(self.analysis["run_integrity"]["passed"])
        self.assertFalse(self.analysis["pairwise"]["qwen35_4b_candidate"]["eligible"])
        self.assertFalse(self.analysis["pairwise"]["qwen35_9b_candidate"]["eligible"])

    def test_qwen35_improves_structure_but_not_complete_plans(self):
        metrics = self.analysis["metrics"]
        control = metrics["qwen25_7b_control"]
        candidate_4b = metrics["qwen35_4b_candidate"]
        candidate_9b = metrics["qwen35_9b_candidate"]

        self.assertEqual(control["tool_parse_success_count"], 0)
        self.assertEqual(candidate_4b["tool_parse_success_count"], 12)
        self.assertEqual(candidate_9b["tool_parse_success_count"], 12)
        self.assertGreater(candidate_4b["exact_field_accuracy"], control["exact_field_accuracy"])
        self.assertGreater(candidate_9b["exact_field_accuracy"], control["exact_field_accuracy"])
        self.assertEqual(candidate_4b["exact_case_count"], 2)
        self.assertEqual(candidate_9b["exact_case_count"], 2)
        self.assertLess(candidate_4b["exact_case_accuracy"], 0.9)
        self.assertLess(candidate_9b["exact_case_accuracy"], 0.9)

    def test_no_production_change_is_authorized(self):
        lock_path = ROOT / "configs/cognitive_plan_model_screen_v65_result_lock.json"
        self.assertTrue(lock_path.exists())
        lock = json.loads(lock_path.read_text(encoding="utf-8"))
        for name, artifact in lock["frozen_artifacts"].items():
            digest = hashlib.sha256((ROOT / artifact["path"]).read_bytes()).hexdigest()
            self.assertEqual(digest, artifact["sha256"], name)
        self.assertFalse(lock["authorizations"]["production_model_replacement"])
        self.assertFalse(lock["authorizations"]["production_runtime_change"])


if __name__ == "__main__":
    unittest.main()
