import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REPORT_JSON = ROOT / "reports/public_persona_reference_manifest_v2_audit.json"
REPORT_MD = ROOT / "reports/public_persona_reference_manifest_v2_audit.md"
HARNESS_LOCK = ROOT / "configs/public_persona_reference_manifest_v2_harness_lock.json"
RESULT_LOCK = ROOT / "configs/public_persona_reference_manifest_v2_result_lock.json"


class PublicPersonaReferenceManifestV2ResultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = json.loads(REPORT_JSON.read_text(encoding="utf-8"))
        cls.harness = json.loads(HARNESS_LOCK.read_text(encoding="utf-8"))
        cls.lock = json.loads(RESULT_LOCK.read_text(encoding="utf-8"))

    def test_result_artifacts_match_result_lock(self):
        for artifact in self.lock["frozen_artifacts"].values():
            path = ROOT / artifact["path"]
            self.assertEqual(
                hashlib.sha256(path.read_bytes()).hexdigest(), artifact["sha256"]
            )

    def test_harness_artifacts_match_harness_lock(self):
        for artifact in self.harness["frozen_artifacts"].values():
            path = ROOT / artifact["path"]
            self.assertEqual(
                hashlib.sha256(path.read_bytes()).hexdigest(), artifact["sha256"]
            )

    def test_protocol_passes_without_formal_execution_or_persona_score(self):
        self.assertTrue(self.report["protocol_passed"])
        self.assertFalse(self.report["formal_execution_ready"])
        self.assertFalse(self.report["persona_score_computed"])
        self.assertEqual(
            self.report["decision"],
            "authorize_metadata_only_event_coding_preregistration_and_consent_form_review",
        )
        self.assertEqual(self.report["summary"]["protocol_check_pass_count"], 13)
        self.assertEqual(self.report["summary"]["protocol_check_count"], 13)
        self.assertEqual(self.report["summary"]["readiness_check_pass_count"], 4)
        self.assertEqual(self.report["summary"]["readiness_check_count"], 19)
        self.assertEqual(self.report["violations"], {})

    def test_only_source_governance_readiness_checks_pass(self):
        passed = {
            name for name, value in self.report["readiness_checks"].items() if value
        }
        self.assertEqual(
            passed,
            {
                "target_calibration_source_count",
                "target_final_holdout_source_count",
                "matched_contrast_person_count",
                "all_nonzero_claims_hash_bound",
            },
        )

    def test_source_counts_are_nonzero_but_formal_data_counts_are_zero(self):
        summary = self.report["summary"]
        self.assertEqual(summary["actor_count"], 4)
        self.assertEqual(summary["matched_contrast_person_count"], 3)
        self.assertEqual(summary["official_identity_source_count"], 8)
        self.assertEqual(summary["target_calibration_source_count"], 3)
        self.assertEqual(summary["target_final_holdout_source_count"], 4)
        for field in (
            "target_behavior_event_count",
            "contrast_behavior_event_count",
            "human_rater_count",
            "model_response_count",
            "persona_score_count",
            "holdout_content_review_count",
            "runtime_change_count",
            "model_call_count",
        ):
            self.assertEqual(summary[field], 0, field)

    def test_report_inputs_are_hash_bound(self):
        for artifact in self.report["inputs"].values():
            path = ROOT / artifact["path"]
            self.assertEqual(
                hashlib.sha256(path.read_bytes()).hexdigest(), artifact["sha256"]
            )

    def test_result_authorizes_no_content_collection_model_holdout_or_claim(self):
        authorizations = self.report["authorizations"]
        self.assertTrue(authorizations["metadata_only_event_coding_preregistration"])
        self.assertTrue(authorizations["consent_form_review"])
        for field in (
            "behavior_content_coding",
            "rater_recruitment",
            "rating_collection",
            "model_execution",
            "runtime_change",
            "prompt_change",
            "model_training",
            "sealed_holdout_unsealing",
            "formal_persona_scoring",
            "public_persona_fidelity_claim",
            "private_person_copy_claim",
        ):
            self.assertFalse(authorizations[field], field)

    def test_markdown_states_source_is_not_event_and_no_ratings_exist(self):
        markdown = REPORT_MD.read_text(encoding="utf-8")
        self.assertIn("來源不是事件", markdown)
        self.assertIn("尚未觀看、編碼或建立目標答案", markdown)
        self.assertIn("未招募、未評分", markdown)
        self.assertIn("仍禁止內容編碼", markdown)


if __name__ == "__main__":
    unittest.main()
