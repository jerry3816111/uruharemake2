import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CLOSURE = ROOT / "configs" / "reflection_causal_pilot_v1_result_closure.json"
ANALYSIS = ROOT / "reports" / "reflection_causal_pilot_v1_analysis.json"
DIAGNOSTIC = ROOT / "reports" / "reflection_causal_pilot_v1_runtime_diagnostic.json"


class ReflectionCausalPilotV1ResultTest(unittest.TestCase):
    def test_frozen_result_hashes_match(self):
        closure = json.loads(CLOSURE.read_text(encoding="utf-8"))
        for relative, expected in closure["frozen_results"].items():
            actual = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
            self.assertEqual(actual, expected, relative)

    def test_negative_decision_matches_analyzer(self):
        closure = json.loads(CLOSURE.read_text(encoding="utf-8"))
        analysis = json.loads(ANALYSIS.read_text(encoding="utf-8"))
        self.assertFalse(analysis["summary"]["all_gates_pass"])
        self.assertEqual(closure["decision"], analysis["decision"])
        self.assertEqual(closure["primary_summary"]["paired_behavior_gains"], 0)
        self.assertEqual(closure["primary_summary"]["paired_behavior_regressions"], 2)
        self.assertEqual(closure["primary_summary"]["paired_behavior_net_gain"], -2)
        self.assertFalse(closure["runtime_reflection_change_authorized_by_this_closure"])
        self.assertFalse(closure["large_reflection_run_authorized"])

    def test_runtime_diagnostic_records_bounded_root_cause(self):
        payload = json.loads(DIAGNOSTIC.read_text(encoding="utf-8"))
        self.assertEqual(payload["environment"]["chromadb_version"], "1.5.1")
        self.assertEqual(payload["pilot_observation"]["treatment_rule_writes"], 6)
        self.assertEqual(payload["pilot_observation"]["direct_wisdom_query_matches"], 6)
        self.assertEqual(payload["pilot_observation"]["reflection_rules_in_working_memory"], 0)
        self.assertIn("rejects ids as an include item", payload["root_cause"])
        self.assertIn("direct episode and wisdom text queries still work", payload["scope_boundary"])


if __name__ == "__main__":
    unittest.main()
