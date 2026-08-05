import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
LOCK = ROOT / "configs/answer_bearing_memory_span_model_capacity_v1_result_lock.json"


class AnswerBearingMemorySpanModelCapacityV1ResultTests(unittest.TestCase):
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
            digest = hashlib.sha256((ROOT / artifact["path"]).read_bytes()).hexdigest()
            self.assertEqual(digest, artifact["sha256"])

    def test_no_model_is_selected(self):
        self.assertIsNone(self.lock["selected_model"])
        self.assertIsNone(self.report["selected_model"])
        self.assertEqual(self.lock["decision"], "model_capacity_not_sufficient")
        self.assertFalse(any(row["eligible"] for row in self.report["model_results"]))

    def test_nine_b_improves_but_does_not_pass(self):
        observed = self.lock["observed"]
        self.assertEqual(observed["qwen3.5:9b"]["phase_1_target_only_safe"], "4_of_8")
        self.assertEqual(observed["qwen3.5:9b"]["target_removed_selection_count"], 0)
        self.assertFalse(observed["qwen3.5:9b"]["phase_1_passed"])

    def test_result_authorizes_representation_experiment_only(self):
        authorization = self.lock["authorization"]
        self.assertFalse(authorization["runtime_change"])
        self.assertFalse(authorization["fresh_holdout"])
        self.assertTrue(
            authorization["source_preserving_evidence_representation_experiment"]
        )


if __name__ == "__main__":
    unittest.main()
