from __future__ import annotations

import json
from pathlib import Path
import unittest

from longitudinal_human_model.registry import sha256_file


ROOT = Path(__file__).resolve().parent
RESULT = ROOT / "analysis/m6_behavior_predictor_synthetic_first_generation_raw.json"
LOCK = ROOT / "configs/m6_behavior_predictor_result_lock.json"


class FrozenM6ResultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = json.loads(RESULT.read_text(encoding="utf-8"))
        cls.lock = json.loads(LOCK.read_text(encoding="utf-8"))

    def test_hash_engineering_gate_and_claim_boundary_are_frozen(self):
        self.assertEqual(self.lock["result_sha256"], sha256_file(RESULT))
        self.assertEqual("complete_hypothesis_run", self.result["status"])
        self.assertTrue(self.result["engineering_gate_pass"])
        self.assertFalse(self.result["formal_target_claim"])

    def test_all_41_fresh_model_calls_are_retained_once(self):
        records = self.result["provider_records"]
        self.assertEqual(41, len(records))
        self.assertEqual(list(range(1, 42)), [row["call_index"] for row in records])
        self.assertEqual({"qwen3.5:9b"}, {row["model_reported"] for row in records})
        self.assertTrue(all(row["raw_response"] for row in records))

    def test_narrow_synthetic_lift_and_quiet_success_failure_both_remain_visible(self):
        self.assertTrue(self.result["predictive_lift_supported"])
        ours = self.result["metrics"]["OURS_HYBRID"]
        self.assertAlmostEqual(0.875, ours["top1_accuracy"])
        self.assertAlmostEqual(0.15091062389155593, ours["brier_score"])
        failure = next(
            row for row in self.result["rows"]
            if row["condition"] == "OURS_HYBRID" and row["sample_id"] == "quiet_success::holdout"
        )
        self.assertEqual("acknowledge_then_continue", failure["actual_observed_behavior"])
        self.assertEqual("direct_rejection", failure["selected_behavior"])
        self.assertGreater(failure["probabilities"]["direct_rejection"], 0.77)

    def test_behavior_stage_never_performs_language_realization(self):
        self.assertTrue(all(row["language_realization_performed"] is False for row in self.result["rows"]))
        self.assertTrue(all(
            row["explanation"]["kind"] == "direct_model_contributions_not_posthoc_llm"
            for row in self.result["rows"] if row["condition"] == "OURS_HYBRID"
        ))


if __name__ == "__main__":
    unittest.main()
