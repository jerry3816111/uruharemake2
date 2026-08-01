import hashlib
import json
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
LOCK = ROOT / "configs/persona_policy_compute_seam_v1_compat_repair_result_lock.json"
REPORT = ROOT / "reports/persona_policy_compute_seam_v1_compat_repair.json"
REPORT_MD = ROOT / "reports/persona_policy_compute_seam_v1_compat_repair.md"


class PersonaPolicyComputeSeamCompatRepairResultTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lock = json.loads(LOCK.read_text(encoding="utf-8"))
        cls.report = json.loads(REPORT.read_text(encoding="utf-8"))

    def test_frozen_artifact_hashes_match(self):
        historical = {"repaired_runtime_integration", "expanded_seam_tests"}
        for name, artifact in self.lock["frozen_artifacts"].items():
            if name in historical:
                content = subprocess.run(
                    [
                        "git",
                        "show",
                        f"{self.lock['formal_git_head']}:{artifact['path']}",
                    ],
                    cwd=ROOT,
                    check=True,
                    capture_output=True,
                ).stdout
            else:
                content = (ROOT / artifact["path"]).read_bytes()
            self.assertEqual(
                hashlib.sha256(content).hexdigest(),
                artifact["sha256"],
                artifact["path"],
            )

    def test_formal_git_head_exists(self):
        completed = subprocess.run(
            ["git", "cat-file", "-e", f"{self.lock['formal_git_head']}^{{commit}}"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_failure_is_retained_and_repair_is_complete(self):
        result = self.lock["formal_result"]
        self.assertEqual(result["pre_repair_regression_test_count"], 164)
        self.assertEqual(result["pre_repair_regression_pass_count"], 163)
        self.assertEqual(result["pre_repair_error_count"], 1)
        self.assertEqual(result["post_repair_regression_test_count"], 165)
        self.assertEqual(result["post_repair_regression_pass_count"], 165)
        self.assertEqual(result["post_repair_error_count"], 0)
        self.assertEqual(result["seam_test_count"], 16)
        self.assertEqual(result["seam_test_pass_count"], 16)

    def test_authorization_remains_narrow(self):
        authorization = self.lock["authorizations"]
        self.assertTrue(authorization["merge_persona_policy_compute_seam"])
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

    def test_report_preserves_no_model_boundary(self):
        formal = self.report["formal_after_repair"]
        self.assertEqual(formal["actual_model_call_count"], 0)
        self.assertEqual(formal["holdout_content_review_count"], 0)
        self.assertEqual(formal["persona_score_count"], 0)
        self.assertFalse(self.report["repair"]["response_logic_change"])
        self.assertFalse(self.report["repair"]["persona_policy_change"])

    def test_markdown_explains_before_and_after(self):
        markdown = REPORT_MD.read_text(encoding="utf-8")
        self.assertIn("163/164 通過", markdown)
        self.assertIn("165 / 165", markdown)
        self.assertIn("367 個固定回覆字串", markdown)


if __name__ == "__main__":
    unittest.main()
