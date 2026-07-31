import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
LOCK_PATH = ROOT / "configs/public_persona_missing_role_v8_model_result_lock.json"


class PublicPersonaMissingRoleV8ModelResultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
        cls.raw = json.loads(
            (ROOT / cls.lock["artifacts"]["raw"]["path"]).read_text(encoding="utf-8")
        )
        cls.analysis = json.loads(
            (ROOT / cls.lock["artifacts"]["analysis_json"]["path"]).read_text(
                encoding="utf-8"
            )
        )

    def test_artifact_hashes_match(self):
        for artifact in self.lock["artifacts"].values():
            path = ROOT / artifact["path"]
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), artifact["sha256"])

    def test_exact_execution_and_negative_decision(self):
        self.assertEqual(self.raw["git_head"], self.lock["git_head"])
        self.assertEqual(self.raw["completed_model_call_count"], 40)
        self.assertEqual(len(self.raw["rows"]), 40)
        self.assertTrue(self.analysis["integrity"]["passed"])
        self.assertFalse(self.analysis["passed"])
        self.assertEqual(self.analysis["decision"], self.lock["decision"])

    def test_locked_metrics_show_inert_single_case_projection(self):
        metrics = self.lock["metrics"]
        analysis_metrics = self.analysis["metrics"]
        comparison = self.analysis["comparison"]
        self.assertEqual(metrics["control_v4_persona"], 12)
        self.assertEqual(metrics["treatment_v4_persona"], 12)
        self.assertEqual(
            analysis_metrics["c0_existing_speech_plan"]["v4_persona_pass_count"],
            metrics["control_v4_persona"],
        )
        self.assertEqual(
            analysis_metrics["t1_missing_role_tokens"]["v4_persona_pass_count"],
            metrics["treatment_v4_persona"],
        )
        self.assertEqual(metrics["new_v4_persona_passes"], 0)
        self.assertEqual(metrics["v4_persona_regressions"], 0)
        self.assertEqual(metrics["semantic_contract_regressions"], 0)
        self.assertEqual(metrics["surface_gate_regressions"], 0)
        self.assertEqual(metrics["specificity_intrusion_regressions"], 0)
        self.assertEqual(comparison["new_v4_persona_passes"], 0)
        self.assertEqual(comparison["v4_persona_regressions"], 0)
        self.assertEqual(comparison["semantic_contract_regressions"], 0)
        self.assertEqual(comparison["surface_gate_regressions"], 0)
        self.assertEqual(comparison["specificity_intrusion_regressions"], 0)
        self.assertEqual(metrics["unchanged_case_reply_identity_count"], 19)
        self.assertEqual(metrics["changed_case_reply_identity_count"], 1)
        changed_rows = [
            row for row in self.raw["rows"] if row["role_projection_active"]
        ]
        self.assertEqual(len(changed_rows), 2)
        self.assertEqual(
            len({row["raw_reply_sha256"] for row in changed_rows}),
            metrics["changed_case_reply_identity_count"],
        )

    def test_only_model_readable_role_semantics_research_is_authorized(self):
        authorization = "model_readable_missing_role_semantics_research"
        self.assertTrue(self.lock["authorizations"][authorization])
        for name, value in self.lock["authorizations"].items():
            if name != authorization:
                self.assertFalse(value)
        self.assertEqual(self.raw["v2_holdout_content_review_count"], 0)
        self.assertEqual(self.raw["production_memory_write_count"], 0)
        self.assertEqual(self.raw["physical_vrm_action_count"], 0)


if __name__ == "__main__":
    unittest.main()
