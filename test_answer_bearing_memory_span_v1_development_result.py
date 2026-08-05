import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
LOCK = ROOT / "configs/answer_bearing_memory_span_v1_development_result_lock.json"


class AnswerBearingMemorySpanV1DevelopmentResultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lock = json.loads(LOCK.read_text(encoding="utf-8"))
        cls.report = json.loads(
            (ROOT / cls.lock["artifacts"]["report_json"]["path"]).read_text(
                encoding="utf-8"
            )
        )

    def test_artifacts_are_hash_locked(self):
        for artifact in self.lock["artifacts"].values():
            actual = hashlib.sha256((ROOT / artifact["path"]).read_bytes()).hexdigest()
            self.assertEqual(actual, artifact["sha256"])

    def test_locked_metrics_match_report(self):
        observed = self.lock["observed"]
        metrics = self.report["metrics"]
        for key in (
            "wrong_trace_selection_count",
            "target_removed_selection_count",
            "intact_safe_outcome_rate",
            "replacement_safe_outcome_rate",
            "irrelevant_removed_target_selection_rate",
            "structured_parse_rate",
            "exact_span_grounding_rate",
            "mean_latency_seconds",
            "p95_latency_seconds",
        ):
            self.assertEqual(observed[key], metrics[key])
        self.assertEqual(self.report["decision"], self.lock["decision"])

    def test_safety_gain_is_not_misreported_as_capability_gain(self):
        observed = self.lock["observed"]
        self.assertEqual(observed["wrong_trace_selection_count"], 0)
        self.assertEqual(observed["target_removed_selection_count"], 0)
        self.assertEqual(observed["intact_safe_outcome_rate"], 0.125)
        self.assertEqual(self.lock["status"], "development_rejected_locked")

    def test_no_runtime_or_holdout_authorization(self):
        authorization = self.lock["authorization"]
        self.assertFalse(authorization["runtime_change"])
        self.assertFalse(authorization["production_enablement"])
        self.assertFalse(authorization["fresh_holdout"])
        self.assertTrue(authorization["local_model_capacity_screen_on_consumed_data"])


if __name__ == "__main__":
    unittest.main()
