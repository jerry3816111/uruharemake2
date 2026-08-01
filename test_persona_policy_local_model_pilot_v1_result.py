import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
LOCK = ROOT / "configs/persona_policy_local_model_pilot_v1_result_lock.json"
RESULT = ROOT / "reports/persona_policy_local_model_pilot_v1_result.json"
FINAL = ROOT / "reports/persona_policy_local_model_pilot_v1_final_review.json"
FINAL_MD = ROOT / "reports/persona_policy_local_model_pilot_v1_final_review.md"


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class PersonaPolicyLocalModelPilotV1ResultTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lock = json.loads(LOCK.read_text(encoding="utf-8"))
        cls.result = json.loads(RESULT.read_text(encoding="utf-8"))
        cls.final = json.loads(FINAL.read_text(encoding="utf-8"))

    def test_all_formal_artifact_hashes_match(self):
        for artifact in self.lock["frozen_artifacts"].values():
            self.assertEqual(
                sha256_file(ROOT / artifact["path"]),
                artifact["sha256"],
                artifact["path"],
            )

    def test_formal_failure_is_preserved_not_relabelled(self):
        self.assertEqual(self.result["status"], "pilot_failed")
        self.assertEqual(self.final["formal_status"], "pilot_failed")
        self.assertEqual(self.final["formal_result"], self.lock["formal_result"])
        self.assertFalse(self.result["checks"]["enough_strict_valid_pairs"])
        self.assertFalse(self.result["checks"]["observable_policy_sensitivity"])

    def test_compute_was_fair_and_actual_model_ran(self):
        formal = self.lock["formal_result"]
        self.assertEqual(formal["actual_model_generation_call_count"], 10)
        self.assertEqual(formal["nonempty_raw_generation_count"], 10)
        self.assertEqual(formal["allocated_prompt_tokens_each"], 640)
        self.assertTrue(formal["compute_parity_pass"])
        self.assertEqual(formal["legacy_fixed_surface_access_count"], 0)

    def test_no_persona_or_runtime_claim_is_authorized(self):
        authorizations = self.final["authorizations"]
        self.assertTrue(authorizations["merge_negative_pilot_evidence"])
        self.assertTrue(authorizations["matched_base_only_vs_adapter_diagnostic"])
        for field in (
            "build_blinded_policy_direction_coding_bundle",
            "formal_persona_similarity_claim",
            "production_default_enablement",
            "model_training",
            "sealed_holdout_unsealing",
            "public_impersonation",
        ):
            self.assertFalse(authorizations[field], field)

    def test_posthoc_diagnostic_is_separate_from_formal_score(self):
        diagnostic = self.lock["posthoc_diagnostic_not_used_for_pass_fail"]
        self.assertEqual(diagnostic["likely_semantic_gate_false_positive_count"], 1)
        self.assertEqual(diagnostic["case_id"], "persona_local_pilot_03")
        self.assertFalse(self.final["diagnosis"]["full_persona_disabled_control_present"])

    def test_markdown_explains_failure_and_control_limit(self):
        markdown = FINAL_MD.read_text(encoding="utf-8")
        self.assertIn("正式 pilot 失敗", markdown)
        self.assertIn("2/10", markdown)
        self.assertIn("base-only", markdown)
        self.assertIn("不是完整的「無人格模型」對照", markdown)


if __name__ == "__main__":
    unittest.main()
