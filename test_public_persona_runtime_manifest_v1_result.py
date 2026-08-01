import json
import subprocess
import unittest
from pathlib import Path

import public_persona_runtime_manifest_v1 as v1


ROOT = Path(__file__).resolve().parent
RESULT_LOCK = ROOT / "configs/public_persona_runtime_manifest_v1_result_lock.json"
REPORT_JSON = ROOT / "reports/public_persona_runtime_manifest_v1_construction.json"
REPORT_MD = ROOT / "reports/public_persona_runtime_manifest_v1_construction.md"


class PublicPersonaRuntimeManifestV1ResultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lock = json.loads(RESULT_LOCK.read_text(encoding="utf-8"))
        cls.report = json.loads(REPORT_JSON.read_text(encoding="utf-8"))

    def test_all_frozen_artifact_hashes_match(self):
        for artifact in self.lock["frozen_artifacts"].values():
            path = ROOT / artifact["path"]
            self.assertTrue(path.is_file(), artifact["path"])
            self.assertEqual(artifact["sha256"], v1.sha256_file(path), artifact["path"])

    def test_formal_git_head_exists_and_precedes_result_lock(self):
        formal_head = self.lock["formal_git_head"]
        self.assertRegex(formal_head, r"^[0-9a-f]{40}$")
        completed = subprocess.run(
            ["git", "cat-file", "-e", f"{formal_head}^{{commit}}"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(0, completed.returncode, completed.stderr)

    def test_construction_passed_all_twenty_six_checks(self):
        result = self.lock["formal_result"]
        self.assertTrue(self.lock["construction_passed"])
        self.assertEqual(26, result["construction_check_count"])
        self.assertEqual(26, result["construction_check_pass_count"])
        self.assertEqual(26, self.report["counts"]["check_pass_count"])

    def test_only_current_s0_is_executable(self):
        readiness = self.report["condition_readiness"]
        result = self.lock["formal_result"]
        self.assertEqual(4, result["condition_count"])
        self.assertEqual(1, result["executable_condition_count"])
        self.assertEqual(
            ["s0_current_full_cognitive_persona"],
            readiness["executable_condition_ids"],
        )
        self.assertFalse(readiness["formal_comparative_execution_ready"])

    def test_c1_and_c2_remain_blocked_not_fabricated(self):
        blocked = set(self.report["condition_readiness"]["blocked_condition_ids"])
        self.assertEqual(
            {"c1_matched_direct_control", "c2_matched_persona_disabled"},
            blocked,
        )
        self.assertEqual(2, self.lock["formal_result"]["blocked_condition_count"])
        self.assertFalse(self.lock["authorizations"]["matched_control_execution"])

    def test_current_s0_limit_is_quantified(self):
        evidence = self.report["source_audit"]["persona_crosscut_evidence"]
        runtime = self.report["formal_runtime"]
        self.assertEqual(367, evidence["rightbrain_fixed_reply_literal_count"])
        self.assertTrue(runtime["fixed_reply_family_present"])
        self.assertFalse(runtime["meets_no_fixed_reply_long_term_goal"])
        self.assertFalse(runtime["rightbrain_qwen_lora_generation_active"])
        self.assertFalse(runtime["typed_reflection_active"])

    def test_no_model_holdout_memory_runtime_or_persona_result_was_created(self):
        result = self.lock["formal_result"]
        for field in (
            "model_call_count",
            "holdout_content_review_count",
            "production_memory_write_count",
            "runtime_change_count",
            "prompt_change_count",
            "model_weight_change_count",
            "persona_score_count",
        ):
            self.assertEqual(0, result[field], field)

    def test_authorization_is_limited_to_next_design_seam(self):
        authorization = self.lock["authorizations"]
        self.assertTrue(authorization["current_s0_runtime_manifest_frozen"])
        self.assertTrue(authorization["persona_policy_injection_seam_design"])
        for field in (
            "matched_control_execution",
            "model_execution",
            "runtime_change",
            "prompt_change",
            "memory_change",
            "model_training",
            "sealed_holdout_unsealing",
            "formal_persona_scoring",
            "public_persona_fidelity_claim",
            "private_person_copy_claim",
        ):
            self.assertFalse(authorization[field], field)

    def test_result_lock_matches_report_counts_and_decision(self):
        self.assertEqual(v1.PASS_DECISION, self.lock["decision"])
        self.assertEqual(self.report["decision"], self.lock["decision"])
        for field, value in self.lock["formal_result"].items():
            if field in self.report["counts"]:
                self.assertEqual(value, self.report["counts"][field], field)

    def test_markdown_states_fixed_reply_and_control_boundaries(self):
        markdown = REPORT_MD.read_text(encoding="utf-8")
        self.assertIn("367 個固定回覆字串", markdown)
        self.assertIn("C1 同資源直接回答", markdown)
        self.assertIn("C2 關閉人格", markdown)
        self.assertIn("正式比較仍未就緒", markdown)
        self.assertIn("沒有證明人格相似度提高", markdown)


if __name__ == "__main__":
    unittest.main()
