import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RESULT = ROOT / "reports/planner_model_compatibility_v74_screen.json"


class PlannerModelCompatibilityV74ResultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = json.loads(RESULT.read_text(encoding="utf-8"))

    def test_screen_stops_before_formal_claims(self):
        self.assertEqual(self.result["decision"], "reject_direct_qwen35_planner_model_swap")
        self.assertEqual(self.result["evidence_class"], "exploratory_transport_and_model_compatibility_screen")
        self.assertFalse(self.result["formal_preregistration_created"])
        self.assertFalse(self.result["formal_holdout_created"])
        self.assertFalse(self.result["formal_inference_run"])
        self.assertFalse(self.result["runtime_changed"])

    def test_native_screen_changes_only_model_specific_inference(self):
        fixed = self.result["fixed_native_api_conditions"]
        self.assertTrue(fixed["same_leftbrain_messages"])
        self.assertTrue(fixed["same_full_three_candidate_contract"])
        self.assertTrue(fixed["same_bdi_fields"])
        self.assertEqual(fixed["temperature"], 0)
        self.assertEqual(fixed["seed"], 20260774)
        self.assertEqual(fixed["num_predict"], 3072)

    def test_all_three_models_have_bounded_observations(self):
        rows = {row["model"]: row for row in self.result["matched_native_results"]}
        self.assertEqual(set(rows), {"qwen2.5:7b", "qwen3.5:4b", "qwen3.5:9b"})
        for row in rows.values():
            self.assertTrue(row["json_parsed"])
            self.assertEqual(row["candidate_count"], 3)
            self.assertGreater(row["elapsed_seconds"], 0)
            self.assertGreater(row["output_tokens"], 0)
            self.assertTrue(row["quality_issues"])
        self.assertIsNone(self.result["candidate_qualified_for_formal_test"])

    def test_probe_is_excluded_and_rejected_swap_is_not_in_runtime(self):
        self.assertTrue(self.result["screen_input"]["must_be_excluded_from_future_formal_holdouts"])
        runtime = (ROOT / "uruha_brain_mac.py").read_text(encoding="utf-8")
        self.assertNotIn("planner_model_compatibility_v74", runtime)


if __name__ == "__main__":
    unittest.main()
