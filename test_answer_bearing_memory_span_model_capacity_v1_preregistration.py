import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PREREG = ROOT / "configs/answer_bearing_memory_span_model_capacity_v1_preregistration.json"


class AnswerBearingMemorySpanModelCapacityV1PreregistrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = json.loads(PREREG.read_text(encoding="utf-8"))

    def test_frozen_artifacts_match(self):
        for artifact in self.payload["frozen_artifacts"].values():
            digest = hashlib.sha256((ROOT / artifact["path"]).read_bytes()).hexdigest()
            self.assertEqual(digest, artifact["sha256"])

    def test_only_model_size_changes(self):
        variable = self.payload["single_changed_variable"]
        self.assertEqual(variable["name"], "local_model_parameter_size")
        self.assertEqual(len(variable["levels"]), 4)
        self.assertIn("semantic prompt bytes", variable["unchanged"])
        self.assertIn("metrics and decision gates", variable["unchanged"])

    def test_staged_gate_preserves_safety_and_recall(self):
        staged = self.payload["staged_execution"]
        self.assertEqual(staged["phase_1_decisions_per_new_model"], 16)
        self.assertEqual(
            staged["phase_1_pass_gates"]["target_only_safe_outcome_rate_at_least"],
            0.75,
        )
        self.assertTrue(
            staged["phase_1_pass_gates"]["target_removed_selection_count_equals_zero"]
        )

    def test_smallest_passing_model_wins(self):
        rule = self.payload["selection_rule"]
        self.assertIn("smallest eligible model", rule["primary"])
        self.assertEqual(
            [row["tag"] for row in self.payload["models"]],
            ["qwen3.5:0.8b", "qwen3.5:2b", "qwen3.5:4b", "qwen3.5:9b"],
        )

    def test_result_cannot_enable_runtime(self):
        boundary = self.payload["evidence_boundary"]
        self.assertFalse(boundary["runtime_integration"])
        self.assertFalse(boundary["production_enablement"])


if __name__ == "__main__":
    unittest.main()
