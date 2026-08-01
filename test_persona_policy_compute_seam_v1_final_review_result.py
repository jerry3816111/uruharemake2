import hashlib
import json
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
LOCK = ROOT / "configs/persona_policy_compute_seam_v1_final_review_result_lock.json"
REPORT = ROOT / "reports/persona_policy_compute_seam_v1_final_review.json"
REPORT_MD = ROOT / "reports/persona_policy_compute_seam_v1_final_review.md"


class PersonaPolicyComputeSeamFinalReviewResultTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lock = json.loads(LOCK.read_text(encoding="utf-8"))
        cls.report = json.loads(REPORT.read_text(encoding="utf-8"))

    def test_frozen_artifact_hashes_match(self):
        historical = {"compute_ledger", "runtime_integration", "seam_tests"}
        for name, artifact in self.lock["frozen_artifacts"].items():
            if name in historical:
                content = subprocess.run(
                    ["git", "show", f"{self.lock['formal_git_head']}:{artifact['path']}"],
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

    def test_all_review_findings_are_closed(self):
        closed = self.report["closed_findings"]
        self.assertTrue(closed)
        self.assertTrue(all(closed.values()))
        result = self.lock["formal_result"]
        self.assertEqual(result["expanded_related_regression_test_count"], 172)
        self.assertEqual(result["expanded_related_regression_pass_count"], 172)
        self.assertEqual(result["expanded_related_regression_error_count"], 0)
        self.assertEqual(result["seam_test_count"], 17)
        self.assertEqual(result["seam_test_pass_count"], 17)

    def test_authorization_remains_narrow(self):
        authorization = self.lock["authorizations"]
        self.assertTrue(authorization["merge_persona_policy_compute_seam"])
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

    def test_no_model_or_holdout_evidence_is_claimed(self):
        formal = self.report["formal_result"]
        self.assertEqual(formal["actual_model_call_count"], 0)
        self.assertEqual(formal["holdout_content_review_count"], 0)
        self.assertEqual(formal["persona_score_count"], 0)

    def test_markdown_names_function_calling_and_remaining_blocker(self):
        markdown = REPORT_MD.read_text(encoding="utf-8")
        self.assertIn("Function Calling", markdown)
        self.assertIn("172/172", markdown)
        self.assertIn("367 個固定回覆字串", markdown)


if __name__ == "__main__":
    unittest.main()
