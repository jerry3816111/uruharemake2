from __future__ import annotations

import json
from pathlib import Path
import unittest

from longitudinal_human_model.registry import sha256_file


ROOT = Path(__file__).resolve().parent
RESULT = ROOT / "analysis/m5_state_transition_synthetic_first_generation_raw.json"
LOCK = ROOT / "configs/m5_state_transition_result_lock.json"


class FrozenM5ResultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = json.loads(RESULT.read_text(encoding="utf-8"))
        cls.lock = json.loads(LOCK.read_text(encoding="utf-8"))

    def test_result_hash_and_first_generation_status_are_frozen(self):
        self.assertEqual(self.lock["result_sha256"], sha256_file(RESULT))
        self.assertEqual("complete_mechanism_run", self.result["status"])
        self.assertTrue(self.result["gate_pass"])
        self.assertFalse(self.result["formal_target_claim"])

    def test_actual_qwen_calls_are_complete_without_hidden_retry_rows(self):
        rows = self.result["feature_extraction"]["records"]
        self.assertEqual(40, len(rows))
        self.assertEqual(40, len({row["example_id"] for row in rows}))
        self.assertEqual({"qwen3.5:9b"}, {row["model_reported"] for row in rows})
        self.assertTrue(all(row["raw_response"] for row in rows))
        self.assertEqual(40, self.result["resource_accounting"]["model_call_count"])

    def test_t3_bottleneck_is_preserved_instead_of_claimed_as_best(self):
        families = self.result["families"]
        self.assertLess(families["T2_LINEAR"]["metrics"]["rmse"], families["T3_HYBRID"]["metrics"]["rmse"])
        self.assertLess(families["T1_WEIGHTED"]["metrics"]["rmse"], families["T3_HYBRID"]["metrics"]["rmse"])
        self.assertLess(families["T3_HYBRID"]["metrics"]["rmse"], families["T0_STATIC"]["metrics"]["rmse"])
        self.assertAlmostEqual(0.229375, self.result["feature_extraction"]["quality"]["holdout"]["mae"])

    def test_no_behavior_or_language_stage_was_smuggled_into_m5(self):
        traces = [trace for family in self.result["families"].values() for trace in family["traces"]]
        self.assertTrue(all(trace["behavior_prediction_performed"] is False for trace in traces))
        self.assertTrue(all(trace["language_generation_performed"] is False for trace in traces))


if __name__ == "__main__":
    unittest.main()
