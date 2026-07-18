import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PREREG = ROOT / "configs/adaptive_ordinary_planner_v73_preregistration.json"
RESULT = ROOT / "reports/adaptive_ordinary_planner_v73_development_screen.json"


class AdaptiveOrdinaryPlannerV73ResultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.prereg = json.loads(PREREG.read_text(encoding="utf-8"))
        cls.result = json.loads(RESULT.read_text(encoding="utf-8"))

    def test_negative_result_stops_before_formal_holdout(self):
        self.assertEqual(self.result["decision"], "reject_v73_compact_same_model_planner")
        self.assertFalse(self.result["formal_holdout_constructed"])
        self.assertFalse(self.result["formal_inference_run"])
        self.assertFalse(self.result["runtime_changed"])
        self.assertFalse((ROOT / "datasets/adaptive_ordinary_planner_v73.json").exists())

    def test_two_calibration_rounds_preserve_raw_cost_evidence(self):
        rounds = self.result["compact_contract_calibration"]
        self.assertEqual(set(rounds), {"round_1", "round_2"})
        for evidence in rounds.values():
            self.assertEqual(evidence["valid_count"], 4)
            self.assertEqual(evidence["accepted_count"], 4)
            self.assertEqual(len(evidence["elapsed_seconds"]), 4)
            self.assertEqual(len(evidence["completion_tokens"]), 4)

    def test_development_inputs_are_explicitly_excluded(self):
        excluded = set(self.prereg["problem_evidence"]["development_inputs_must_not_enter_formal_holdout"])
        observed = {row["case_id"] for row in self.result["full_chat_development_probe"]}
        self.assertEqual(observed, excluded)

    def test_rejected_bridge_is_absent_from_runtime(self):
        runtime = (ROOT / "uruha_brain_mac.py").read_text(encoding="utf-8")
        self.assertNotIn("adaptive_planner_shadow_request", runtime)
        self.assertNotIn("think_adaptive_shadow", runtime)


if __name__ == "__main__":
    unittest.main()
