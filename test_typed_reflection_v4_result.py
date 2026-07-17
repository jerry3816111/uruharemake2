import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CLOSURE = ROOT / "configs" / "typed_reflection_v4_result_closure.json"
ANALYSIS = ROOT / "reports" / "typed_reflection_v4_development_analysis.json"


class TypedReflectionV4ResultTest(unittest.TestCase):
    def test_result_hashes_and_failed_behavior_decision_are_frozen(self):
        closure = json.loads(CLOSURE.read_text(encoding="utf-8"))
        analysis = json.loads(ANALYSIS.read_text(encoding="utf-8"))
        for relative, expected in closure["result_artifacts"].items():
            actual = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
            self.assertEqual(actual, expected, relative)
        self.assertEqual(analysis["decision"], closure["automated_decision"])
        self.assertEqual(analysis["summary"]["paired_behavior_gains"], 0)
        self.assertEqual(analysis["summary"]["paired_behavior_regressions"], 2)
        self.assertEqual(analysis["summary"]["paired_behavior_net_gain"], -2)

    def test_posthoc_warning_does_not_overwrite_preregistered_scores(self):
        closure = json.loads(CLOSURE.read_text(encoding="utf-8"))
        audit = closure["posthoc_metric_audit"]
        self.assertEqual(audit["status"], "diagnostic_only_not_a_preregistered_rescore")
        self.assertEqual(len(audit["observations"]), 3)
        self.assertEqual(closure["metrics"]["reported_japanese_surface_quality_rate"], 1.0)
        self.assertIn("proxy", audit["measurement_warning"])

    def test_failed_pilot_authorizes_no_deployment_or_holdout(self):
        closure = json.loads(CLOSURE.read_text(encoding="utf-8"))
        self.assertFalse(closure["deployment_authorized"])
        self.assertFalse(closure["independent_holdout_authorized"])
        self.assertFalse(closure["large_scale_run_authorized"])
        self.assertIn("semantic_fidelity", closure["next_primary_task"])


if __name__ == "__main__":
    unittest.main()
