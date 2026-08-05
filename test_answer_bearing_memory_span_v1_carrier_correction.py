import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
LOCK = ROOT / "configs/answer_bearing_memory_span_v1_carrier_correction_lock.json"


class AnswerBearingMemorySpanV1CarrierCorrectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lock = json.loads(LOCK.read_text(encoding="utf-8"))

    def test_failed_artifacts_are_preserved_exactly(self):
        for artifact in self.lock["failed_artifacts"].values():
            digest = hashlib.sha256((ROOT / artifact["path"]).read_bytes()).hexdigest()
            self.assertEqual(digest, artifact["sha256"])

    def test_only_carrier_thinking_is_changed(self):
        correction = self.lock["single_correction"]
        self.assertEqual(correction["request_field"], "think")
        self.assertFalse(correction["after"])
        self.assertIn("prompt text", self.lock["unchanged"])
        self.assertIn("metrics and decision gates", self.lock["unchanged"])

    def test_rerun_cannot_be_independent_evidence(self):
        self.assertIn("cannot serve as an independent holdout", self.lock["rerun_boundary"])


if __name__ == "__main__":
    unittest.main()
