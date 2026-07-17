import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CLOSURE = ROOT / "configs" / "reflection_causal_replay_v2_result_closure.json"
ANALYSIS = ROOT / "reports" / "reflection_causal_replay_v2_analysis.json"


class ReflectionCausalReplayV2ResultTest(unittest.TestCase):
    def test_frozen_result_hashes_match(self):
        closure = json.loads(CLOSURE.read_text(encoding="utf-8"))
        for relative, expected in closure["frozen_results"].items():
            actual = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
            self.assertEqual(actual, expected, relative)

    def test_decision_separates_channel_repair_from_reflection_learning(self):
        closure = json.loads(CLOSURE.read_text(encoding="utf-8"))
        analysis = json.loads(ANALYSIS.read_text(encoding="utf-8"))
        self.assertEqual(closure["decision"], analysis["decision"])
        self.assertTrue(analysis["channel_repair_gate_pass"])
        self.assertFalse(analysis["summary"]["all_gates_pass"])
        self.assertEqual(closure["v1_to_v2"]["valid_rule_retrieval_rate"], [0.0, 1.0])
        self.assertEqual(closure["v1_to_v2"]["treatment_behavior_success_rate"], [0.3333, 0.3333])
        self.assertEqual(closure["v1_to_v2"]["paired_behavior_gains"], [0, 0])
        self.assertTrue(closure["reflection_redesign_authorized"])
        self.assertFalse(closure["large_scale_reflection_run_authorized"])
        self.assertFalse(closure["independent_generalization_claim_authorized"])


if __name__ == "__main__":
    unittest.main()
