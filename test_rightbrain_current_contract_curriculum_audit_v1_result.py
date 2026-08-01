import hashlib
import json
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
LOCK_PATH = ROOT / "configs/rightbrain_current_contract_curriculum_audit_v1_result_lock.json"


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class RightBrainCurrentContractCurriculumAuditV1ResultTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
        cls.report = json.loads(
            (ROOT / "reports/rightbrain_current_contract_curriculum_audit_v1.json").read_text(
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
        coverage = self.report["coverage"]
        instruction = self.report["instruction_contract"]
        observed = self.report["observed_failure_alignment"]
        self.assertEqual(
            accounting["documented_contract_stage_exposure_count"],
            findings["documented_contract_stage_exposure_count"],
        )
        self.assertEqual(
            accounting["unique_underlying_training_unit_count"],
            findings["unique_underlying_training_unit_count"],
        )
        self.assertEqual(
            coverage["overall_active_path_coverage"]["coverage"],
            findings["overall_active_path_coverage"],
        )
        self.assertEqual(
            coverage["persona_policy_path_coverage"]["coverage"],
            findings["persona_policy_path_coverage"],
        )
        self.assertEqual(
            coverage["persona_policy_value_coverage"]["coverage"],
            findings["persona_policy_value_coverage"],
        )
        self.assertEqual(
            coverage["documented_training_joint_contract_row_count"],
            findings["documented_training_joint_contract_row_count"],
        )
        self.assertEqual(
            coverage["current_joint_contract_row_count"],
            findings["current_joint_contract_row_count"],
        )
        self.assertEqual(
            instruction["training_rows_with_current_system_instruction"],
            findings["training_rows_with_current_system_instruction"],
        )
        self.assertEqual(
            instruction["rows_still_teaching_no_first_person_private"],
            findings["rows_still_teaching_no_first_person_private"],
        )
        self.assertEqual(
            observed["strict_valid_count"], findings["strict_valid_generation_count"]
        )
        self.assertEqual(observed["generation_count"], findings["generation_count"])
        self.assertEqual(
            self.report["development_separation"]["passed"],
            findings["development_separation_passed"],
        )

    def test_authorization_is_construction_only(self):
        decision = self.lock["decision"]
        self.assertTrue(decision["authorize_curriculum_construction"])
        self.assertFalse(decision["authorize_model_training"])
        self.assertFalse(decision["authorize_production_change"])
        self.assertFalse(decision["authorize_persona_similarity_claim"])
        self.assertFalse(decision["causal_claim_supported"])
        for key, value in decision.items():
            self.assertEqual(value, self.report["decision"][key], key)

    def test_self_review_preserves_runtime_and_data_boundaries(self):
        review = self.lock["self_review"]
        self.assertFalse(review["runtime_files_changed"])
        self.assertEqual(review["model_generation_calls"], 0)
        self.assertEqual(review["model_training_runs"], 0)
        self.assertEqual(review["production_memory_writes"], 0)
        self.assertEqual(review["benchmark_items_added"], 0)
        self.assertEqual(review["target_person_utterances_added"], 0)
        self.assertEqual(review["fixed_replies_added_to_runtime"], 0)


if __name__ == "__main__":
    unittest.main()
