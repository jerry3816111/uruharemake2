import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
LOCK = ROOT / "configs/answer_bearing_memory_span_v1_tool_carrier_lock.json"


class AnswerBearingMemorySpanV1ToolCarrierTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lock = json.loads(LOCK.read_text(encoding="utf-8"))

    def test_schema_failure_artifacts_are_preserved(self):
        for artifact in self.lock["schema_failure_artifacts"].values():
            actual = hashlib.sha256((ROOT / artifact["path"]).read_bytes()).hexdigest()
            self.assertEqual(actual, artifact["sha256"])

    def test_tool_carrier_preserves_semantic_contract(self):
        carrier = self.lock["replacement_carrier"]
        self.assertEqual(carrier["tool_name"], "submit_answer_evidence")
        self.assertEqual(carrier["tool_call_count"], 1)
        self.assertIn("semantic instructions in the prompt", self.lock["unchanged"])
        self.assertIn("metrics and gates", self.lock["unchanged"])

    def test_same_data_run_cannot_make_generalization_claim(self):
        self.assertIn("same-data development", self.lock["evidence_boundary"])


if __name__ == "__main__":
    unittest.main()
