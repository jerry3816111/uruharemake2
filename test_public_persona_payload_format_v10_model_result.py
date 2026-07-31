import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
LOCK_PATH = ROOT / "configs/public_persona_payload_format_v10_model_result_lock.json"


class PublicPersonaPayloadFormatV10ModelResultTests(unittest.TestCase):
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
            self.assertEqual(
                hashlib.sha256(path.read_bytes()).hexdigest(), artifact["sha256"]
            )

    def test_exact_execution_integrity_and_negative_decision(self):
        self.assertEqual(self.raw["git_head"], self.lock["git_head"])
        self.assertEqual(self.raw["completed_model_call_count"], 40)
        self.assertEqual(len(self.raw["rows"]), 40)
        self.assertTrue(self.analysis["integrity"]["passed"])
        self.assertFalse(self.analysis["passed"])
        self.assertEqual(self.analysis["decision"], self.lock["decision"])

    def test_locked_metrics_show_role_semantic_and_persona_regressions(self):
        metrics = self.lock["metrics"]
        control = self.analysis["metrics"]["c0_compact_json"]
        treatment = self.analysis["metrics"]["t1_mixed_lines"]
        comparison = self.analysis["comparison"]
        self.assertEqual(control["role_hit_count"], metrics["control_role_hits"])
        self.assertEqual(treatment["role_hit_count"], metrics["treatment_role_hits"])
        self.assertEqual(control["semantic_pass_count"], metrics["control_semantic_passes"])
        self.assertEqual(
            treatment["semantic_pass_count"], metrics["treatment_semantic_passes"]
        )
        self.assertEqual(comparison["new_role_complete_cases"], 0)
        self.assertEqual(comparison["role_slot_wins"], 0)
        self.assertEqual(comparison["role_slot_regressions"], 4)
        self.assertEqual(comparison["semantic_contract_regressions"], 2)
        self.assertEqual(comparison["v4_persona_regressions"], 3)

    def test_target_remains_missing_and_four_role_cases_regress(self):
        scores = {
            (row["case_id"], row["condition"]): row for row in self.analysis["scores"]
        }
        for condition in ("c0_compact_json", "t1_mixed_lines"):
            self.assertFalse(scores[("persona_v3_notice_01", condition)]["role_complete"])
        observed = []
        for case_id in sorted({row["case_id"] for row in self.analysis["scores"]}):
            control = scores[(case_id, "c0_compact_json")]
            treatment = scores[(case_id, "t1_mixed_lines")]
            if any(
                control["role_hits"][role] and not treatment["role_hits"][role]
                for role in control["role_hits"]
            ):
                observed.append(case_id)
        self.assertEqual(observed, self.lock["regressed_role_cases"])

    def test_no_followup_or_runtime_authorization_and_no_side_effects(self):
        self.assertTrue(all(value is False for value in self.lock["authorizations"].values()))
        self.assertEqual(self.raw["v2_holdout_content_review_count"], 0)
        self.assertEqual(self.raw["production_memory_write_count"], 0)
        self.assertEqual(self.raw["physical_vrm_action_count"], 0)
        self.assertEqual(
            sum(bool(row["transport_error"]) for row in self.raw["rows"]), 0
        )
        self.assertEqual(sum(bool(row["tool_calls"]) for row in self.raw["rows"]), 0)


if __name__ == "__main__":
    unittest.main()
