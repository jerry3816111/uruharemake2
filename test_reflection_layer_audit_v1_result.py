import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CLOSURE = ROOT / "configs" / "reflection_layer_audit_v1_result_closure.json"
ANALYSIS = ROOT / "reports" / "reflection_layer_audit_v1_analysis.json"


class ReflectionLayerAuditV1ResultTest(unittest.TestCase):
    def test_result_hashes_and_rejection_are_frozen(self):
        closure = json.loads(CLOSURE.read_text(encoding="utf-8"))
        analysis = json.loads(ANALYSIS.read_text(encoding="utf-8"))
        for relative, expected in closure["result_artifacts"].items():
            actual = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
            self.assertEqual(actual, expected, relative)
        self.assertEqual(analysis["decision"], closure["decision"])
        self.assertEqual(analysis["summary"]["atomic_relation_accuracy"], 0.75)
        self.assertEqual(analysis["summary"]["critical_false_entailment_count"], 2)

    def test_failed_judge_authorizes_no_v4_or_runtime_use(self):
        closure = json.loads(CLOSURE.read_text(encoding="utf-8"))
        self.assertFalse(closure["post_result_prompt_tuning_authorized"])
        self.assertFalse(closure["v4_layer_diagnosis_authorized"])
        self.assertFalse(closure["runtime_change_authorized"])
        self.assertFalse(closure["independent_holdout_authorized"])
        self.assertIn("exact_source", closure["next_primary_task"])


if __name__ == "__main__":
    unittest.main()
