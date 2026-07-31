import hashlib
import json
import unittest
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent
LOCK_PATH = ROOT / "configs/public_persona_contract_v3_model_result_lock.json"


class PublicPersonaContractV3ModelResultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
        cls.raw = json.loads(
            (ROOT / cls.lock["artifacts"]["raw_result"]["path"]).read_text(encoding="utf-8")
        )
        cls.analysis = json.loads(
            (ROOT / cls.lock["artifacts"]["analysis_json"]["path"]).read_text(encoding="utf-8")
        )

    def test_all_frozen_artifact_hashes_match(self):
        for artifact in self.lock["artifacts"].values():
            path = ROOT / artifact["path"]
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), artifact["sha256"])

    def test_formal_execution_has_exact_paired_accounting(self):
        execution = self.lock["execution"]
        self.assertEqual(self.raw["git_head"], self.lock["git_head"])
        self.assertEqual(self.raw["completed_model_call_count"], execution["completed_model_call_count"])
        self.assertEqual(len(self.raw["rows"]), 40)
        pairs = Counter((row["case_id"], row["condition"]) for row in self.raw["rows"])
        self.assertEqual(len(pairs), 40)
        self.assertTrue(all(count == 1 for count in pairs.values()))
        self.assertEqual({row["model_digest"] for row in self.raw["rows"]}, {execution["model_digest"]})

    def test_negative_decision_and_integrity_are_frozen(self):
        self.assertFalse(self.analysis["passed"])
        self.assertEqual(self.analysis["decision"], self.lock["decision"])
        self.assertTrue(self.analysis["integrity"]["passed"])
        self.assertFalse(self.analysis["model_gates"]["passed"])
        failed = {
            name for name, passed in self.analysis["model_gates"]["checks"].items() if not passed
        }
        self.assertEqual(failed, {"new_persona_passes"})

    def test_locked_metrics_match_analysis(self):
        control = self.analysis["metrics"]["c0_static_persona_brief"]
        treatment = self.analysis["metrics"]["t1_conditional_surface_brief"]
        paired = self.analysis["paired"]
        expected = {
            "control_semantic_pass_rate": control["semantic_contract_pass_rate"],
            "treatment_semantic_pass_rate": treatment["semantic_contract_pass_rate"],
            "control_persona_policy_pass_rate": control["persona_policy_pass_rate"],
            "treatment_persona_policy_pass_rate": treatment["persona_policy_pass_rate"],
            "control_surface_gate_pass_count": control["surface_gate_pass_count"],
            "treatment_surface_gate_pass_count": treatment["surface_gate_pass_count"],
            "newly_persona_policy_passed_vs_control": paired["newly_persona_policy_passed_vs_control"],
            "persona_policy_regressions_vs_control": paired["persona_policy_regressions_vs_control"],
            "inactive_raw_reply_identity_count": paired["inactive_raw_reply_identity_count"],
            "inactive_case_count": paired["inactive_case_count"],
            "control_median_latency_seconds": control["median_latency_seconds"],
            "treatment_median_latency_seconds": treatment["median_latency_seconds"],
        }
        self.assertEqual(expected, self.lock["metrics"])

    def test_no_runtime_training_holdout_or_fidelity_authorization(self):
        self.assertEqual(self.analysis["authorizations"], self.lock["authorizations"])
        self.assertFalse(any(self.lock["authorizations"].values()))
        self.assertEqual(self.raw["v2_holdout_content_review_count"], 0)
        self.assertEqual(self.raw["production_memory_write_count"], 0)
        self.assertEqual(self.raw["physical_vrm_action_count"], 0)


if __name__ == "__main__":
    unittest.main()
