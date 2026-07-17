import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
LOCK = ROOT / "configs" / "reflection_layer_audit_v1_harness_lock.json"


class ReflectionLayerAuditV1HarnessTest(unittest.TestCase):
    def test_harness_lock_hashes_every_causal_input(self):
        lock = json.loads(LOCK.read_text(encoding="utf-8"))
        self.assertEqual(lock["required_run_branch"], "main")
        for relative, expected in lock["frozen_artifacts"].items():
            actual = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
            self.assertEqual(actual, expected, relative)

    def test_no_frozen_result_exists_before_runtime_merge(self):
        lock = json.loads(LOCK.read_text(encoding="utf-8"))
        self.assertFalse(lock["model_inference_on_frozen_cases_performed"])
        self.assertFalse(lock["result_artifacts_present_before_run"])


if __name__ == "__main__":
    unittest.main()
