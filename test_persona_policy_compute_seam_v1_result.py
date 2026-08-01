import hashlib
import json
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RESULT_LOCK = ROOT / "configs/persona_policy_compute_seam_v1_result_lock.json"
REPORT_JSON = ROOT / "reports/persona_policy_compute_seam_v1_construction.json"
REPORT_MD = ROOT / "reports/persona_policy_compute_seam_v1_construction.md"


class PersonaPolicyComputeSeamV1ResultTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lock = json.loads(RESULT_LOCK.read_text(encoding="utf-8"))
        cls.report = json.loads(REPORT_JSON.read_text(encoding="utf-8"))

    def test_all_frozen_artifact_hashes_match(self):
        for artifact in self.lock["frozen_artifacts"].values():
            path = ROOT / artifact["path"]
            self.assertTrue(path.is_file(), artifact["path"])
            self.assertEqual(
                artifact["sha256"],
                hashlib.sha256(path.read_bytes()).hexdigest(),
                artifact["path"],
            )

    def test_formal_git_head_exists(self):
        formal_head = self.lock["formal_git_head"]
        self.assertRegex(formal_head, r"^[0-9a-f]{40}$")
        completed = subprocess.run(
            ["git", "cat-file", "-e", f"{formal_head}^{{commit}}"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_formal_counts_match_report(self):
        result = self.lock["formal_result"]
        self.assertTrue(self.lock["construction_passed"])
        self.assertEqual(result["construction_check_count"], 53)
        self.assertEqual(result["construction_check_pass_count"], 53)
        self.assertEqual(result["synthetic_case_count"], 6)
        for field in (
            "default_vs_legacy_payload_mismatch_count",
            "target_vs_neutral_nonpersona_payload_mismatch_count",
            "target_vs_neutral_structure_mismatch_count",
            "protected_field_mutation_count",
            "actual_model_call_count",
            "holdout_content_review_count",
            "production_memory_write_count",
            "runtime_default_behavior_change_count",
            "persona_score_count",
        ):
            self.assertEqual(result[field], 0, field)
            self.assertEqual(result[field], self.report["counts"][field], field)

    def test_authorization_is_narrow_and_blocker_remains_visible(self):
        authorization = self.lock["authorizations"]
        self.assertTrue(authorization["fixed_surface_family_provider_migration_on_synthetic_inputs"])
        for field in (
            "formal_persona_evaluation",
            "sealed_holdout_unsealing",
            "human_blind_rating",
            "model_training",
            "production_default_enablement",
            "public_persona_fidelity_claim",
            "private_person_copy_claim",
        ):
            self.assertFalse(authorization[field], field)
        blocker = self.lock["remaining_blockers"]
        self.assertEqual(blocker["rightbrain_fixed_reply_literal_count"], 367)
        self.assertFalse(blocker["full_persona_disabled_c2_executable"])
        self.assertFalse(blocker["formal_persona_comparison_ready"])

    def test_report_has_no_generated_persona_evidence(self):
        self.assertEqual(self.report["counts"]["actual_model_call_count"], 0)
        self.assertEqual(self.report["counts"]["persona_score_count"], 0)
        self.assertFalse(self.report["authorizations"]["public_persona_fidelity_claim"])
        for row in self.report["synthetic_cases"]:
            self.assertNotIn("reply", row)
            self.assertNotIn("answer", row)

    def test_markdown_explains_result_and_limit(self):
        markdown = REPORT_MD.read_text(encoding="utf-8")
        self.assertIn("建構檢查：53/53", markdown)
        self.assertIn("367 個固定回覆字串", markdown)
        self.assertIn("沒有證明回答更像一ノ瀬うるは", markdown)
        self.assertIn("不保存使用者輸入或模型回答原文", markdown)


if __name__ == "__main__":
    unittest.main()
