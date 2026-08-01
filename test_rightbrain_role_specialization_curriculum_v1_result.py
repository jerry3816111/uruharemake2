import hashlib
import json
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
LOCK_PATH = ROOT / "configs/rightbrain_role_specialization_curriculum_v1_result_lock.json"


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class RightBrainRoleSpecializationCurriculumV1ResultTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
        cls.report = json.loads(
            (ROOT / "reports/rightbrain_role_specialization_curriculum_v1.json").read_text(
                encoding="utf-8"
            )
        )

    def test_formal_git_head_exists(self):
        subprocess.run(
            ["git", "cat-file", "-e", f"{self.lock['formal_git_head']}^{{commit}}"],
            cwd=ROOT,
            check=True,
        )

    def test_locked_artifact_hashes_match(self):
        for artifact in self.lock["artifacts"]:
            self.assertEqual(
                sha256_file(ROOT / artifact["path"]),
                artifact["sha256"],
                artifact["path"],
            )

    def test_locked_findings_match_report(self):
        findings = self.lock["locked_findings"]
        accounting = self.report["accounting"]
        quality = self.report["quality"]
        balance = self.report["balance"]
        self.assertEqual(accounting["base_case_count"], findings["base_case_count"])
        self.assertEqual(accounting["curriculum_row_count"], findings["curriculum_row_count"])
        self.assertEqual(accounting["unique_payload_count"], findings["unique_payload_count"])
        self.assertEqual(set(balance["provider_counts"].values()), {findings["rows_per_provider"]})
        self.assertEqual(set(balance["memory_mode_counts"].values()), {findings["rows_per_memory_mode"]})
        for key in (
            "joint_contract_coverage",
            "current_persona_policy_path_coverage",
            "current_persona_policy_value_coverage",
            "semantic_contract_pass_rate",
            "memory_policy_pass_rate",
            "runtime_candidate_gate_pass_rate",
            "provider_pair_output_difference_rate",
        ):
            self.assertEqual(quality["rates"][key], findings[key], key)
        self.assertEqual(
            quality["counts"]["unique_normalized_target_count"],
            findings["unique_normalized_target_count"],
        )
        self.assertEqual(
            all(value == 0 for value in self.report["separation"]["checks"].values()),
            findings["all_separation_counts_zero"],
        )

    def test_decision_remains_training_preregistration_only(self):
        self.assertEqual(self.lock["decision"], self.report["decision"])
        decision = self.lock["decision"]
        self.assertTrue(decision["authorize_training_pilot_preregistration"])
        self.assertFalse(decision["authorize_model_training"])
        self.assertFalse(decision["authorize_production_change"])
        self.assertFalse(decision["authorize_persona_similarity_claim"])
        self.assertFalse(decision["authorize_generalization_claim"])
        self.assertFalse(decision["causal_claim_supported"])

    def test_self_review_preserves_research_and_runtime_boundaries(self):
        review = self.lock["self_review"]
        self.assertFalse(review["runtime_files_changed"])
        self.assertEqual(review["model_generation_calls"], 0)
        self.assertEqual(review["model_training_runs"], 0)
        self.assertEqual(review["production_memory_writes"], 0)
        self.assertEqual(review["benchmark_items_added"], 0)
        self.assertEqual(review["target_person_utterances_added"], 0)
        self.assertEqual(review["runtime_fixed_replies_added"], 0)
        self.assertTrue(review["codex_assisted_synthetic_authoring_disclosed"])
        self.assertFalse(review["production_readiness_claimed"])
        self.assertFalse(review["persona_similarity_claimed"])

    def test_broad_regression_failures_are_disclosed_not_hidden(self):
        verification = self.lock["verification"]
        self.assertEqual(verification["targeted_related_test_count"], 29)
        self.assertEqual(verification["targeted_related_pass_count"], 29)
        self.assertEqual(verification["targeted_related_failure_count"], 0)
        self.assertEqual(verification["broad_rightbrain_and_persona_test_count"], 515)
        self.assertEqual(
            verification["broad_pass_count"]
            + verification["broad_failure_count"]
            + verification["broad_error_count"],
            515,
        )
        self.assertFalse(
            verification["known_unrelated_failures"][
                "new_branch_touched_any_failing_historical_artifact"
            ]
        )


if __name__ == "__main__":
    unittest.main()
