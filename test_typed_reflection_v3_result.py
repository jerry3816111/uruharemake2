import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CLOSURE = ROOT / "configs" / "typed_reflection_v3_result_closure.json"
ANALYSIS = ROOT / "reports" / "typed_reflection_v3_development_analysis.json"


class TypedReflectionV3ResultTest(unittest.TestCase):
    def test_result_hashes_and_negative_decision_are_frozen(self):
        closure = json.loads(CLOSURE.read_text(encoding="utf-8"))
        analysis = json.loads(ANALYSIS.read_text(encoding="utf-8"))
        for relative, expected in closure["result_artifacts"].items():
            actual = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
            self.assertEqual(actual, expected, relative)
        self.assertEqual(analysis["decision"], closure["decision"])
        self.assertEqual(analysis["summary"]["treatment_behavior_delta"], 0.0)
        self.assertEqual(analysis["summary"]["expected_rule_write_recall"], 0.0)

    def test_failed_development_pilot_authorizes_no_deployment_or_holdout(self):
        closure = json.loads(CLOSURE.read_text(encoding="utf-8"))
        self.assertFalse(closure["deployment_authorized"])
        self.assertFalse(closure["independent_holdout_authorized"])
        self.assertFalse(closure["large_scale_run_authorized"])
        self.assertIn("non_frozen", closure["next_primary_task"])


if __name__ == "__main__":
    unittest.main()
