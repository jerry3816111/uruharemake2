import hashlib
import json
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
LOCK = ROOT / "configs/persona_surface_provider_migration_v1_result_lock.json"
REPORT = ROOT / "reports/persona_surface_provider_migration_v1_construction.json"
REPORT_MD = ROOT / "reports/persona_surface_provider_migration_v1_construction.md"


class PersonaSurfaceProviderMigrationV1ResultTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lock = json.loads(LOCK.read_text(encoding="utf-8"))
        cls.report = json.loads(REPORT.read_text(encoding="utf-8"))

    def test_formal_git_head_exists(self):
        completed = subprocess.run(
            ["git", "cat-file", "-e", f"{self.lock['formal_git_head']}^{{commit}}"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_frozen_artifacts_match_formal_commit(self):
        for artifact in self.lock["frozen_artifacts"].values():
            completed = subprocess.run(
                ["git", "show", f"{self.lock['formal_git_head']}:{artifact['path']}"],
                cwd=ROOT,
                check=False,
                capture_output=True,
            )
            self.assertEqual(completed.returncode, 0, artifact["path"])
            self.assertEqual(
                hashlib.sha256(completed.stdout).hexdigest(),
                artifact["sha256"],
                artifact["path"],
            )

    def test_locked_counts_match_construction_report(self):
        result = self.lock["formal_result"]
        counts = self.report["counts"]
        self.assertTrue(self.lock["construction_passed"])
        self.assertEqual(result["focused_test_count"], result["focused_test_pass_count"])
        self.assertEqual(
            result["expanded_behavior_test_count"],
            result["expanded_behavior_test_pass_count"],
        )
        for field in (
            "structured_success_case_count",
            "structured_failed_closed_case_count",
            "structured_legacy_fixed_surface_access_count",
            "structured_reachable_fixed_family_entry_count",
            "legacy_runtime_mismatch_count",
            "actual_local_generation_call_count",
            "source_legacy_fixed_reply_literal_count",
            "holdout_content_review_count",
            "production_memory_write_count",
            "persona_score_count",
        ):
            self.assertEqual(result[field], counts[field], field)

    def test_known_historical_hash_failure_is_not_hidden(self):
        limitation = self.lock["known_test_limitation"]
        self.assertEqual(self.lock["formal_result"]["known_stale_historical_hash_test_count"], 1)
        self.assertEqual(
            limitation["classification"],
            "historical_source_hash_lock_bound_to_current_worktree",
        )
        self.assertFalse(limitation["behavioral_regression"])
        self.assertIn("V90", limitation["replacement_evidence"])

    def test_authorization_is_narrow(self):
        authorization = self.lock["authorizations"]
        self.assertTrue(authorization["fresh_local_model_target_vs_neutral_surface_pilot"])
        for field in (
            "formal_persona_similarity_evaluation",
            "sealed_holdout_unsealing",
            "human_blind_rating",
            "model_training",
            "production_default_enablement",
            "public_persona_fidelity_claim",
            "private_person_copy_claim",
        ):
            self.assertFalse(authorization[field], field)

    def test_report_states_runtime_and_source_boundaries(self):
        markdown = REPORT_MD.read_text(encoding="utf-8")
        self.assertIn("structured 固定回覆存取 | 0", markdown)
        self.assertIn("367 個 legacy 固定回覆字串", markdown)
        self.assertIn("不是已刪除原始碼", markdown)
        self.assertIn("不授權正式人格結論", markdown)


if __name__ == "__main__":
    unittest.main()
