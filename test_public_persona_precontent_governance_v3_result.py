import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REPORT_JSON = ROOT / "reports/public_persona_precontent_governance_v3_audit.json"
REPORT_MD = ROOT / "reports/public_persona_precontent_governance_v3_audit.md"
HARNESS_LOCK = (
    ROOT / "configs/public_persona_precontent_governance_v3_harness_lock.json"
)
RESULT_LOCK = (
    ROOT / "configs/public_persona_precontent_governance_v3_result_lock.json"
)


class PublicPersonaPrecontentGovernanceV3ResultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = json.loads(REPORT_JSON.read_text(encoding="utf-8"))
        cls.markdown = REPORT_MD.read_text(encoding="utf-8")
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
            "authorize_bounded_calibration_event_coding_and_consent_usability_review_only",
        )
        self.assertEqual(self.report["summary"]["protocol_check_pass_count"], 16)
        self.assertEqual(self.report["summary"]["protocol_check_count"], 16)
        self.assertEqual(self.report["summary"]["formal_readiness_pass_count"], 4)
        self.assertEqual(self.report["summary"]["formal_readiness_check_count"], 19)
        self.assertEqual(self.report["violations"], {})

    def test_source_reviews_and_content_boundaries_are_exact(self):
        summary = self.report["summary"]
        self.assertEqual(summary["registered_source_review_count"], 17)
        self.assertEqual(summary["calibration_source_authorized_count"], 3)
        self.assertEqual(summary["sealed_final_source_count"], 4)
        self.assertEqual(summary["holdout_content_review_count"], 0)

    def test_no_behavior_rater_model_or_score_data_was_created(self):
        summary = self.report["summary"]
        for field in (
            "behavior_event_count",
            "human_rater_count",
            "model_response_count",
            "persona_score_count",
            "holdout_content_review_count",
            "runtime_change_count",
            "model_call_count",
        ):
            self.assertEqual(summary[field], 0, field)

    def test_authorization_is_calibration_only_and_nonexecuting(self):
        auth = self.report["authorizations"]
        self.assertTrue(auth["bounded_calibration_event_coding"])
        self.assertTrue(auth["consent_form_usability_review"])
        self.assertTrue(auth["contrast_event_source_registration"])
        for field in (
            "rater_recruitment",
            "rating_collection",
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
            self.assertFalse(auth[field], field)

    def test_recruitment_blockers_are_explicitly_unresolved(self):
        blockers = self.report["recruitment_blockers"]
        self.assertEqual(len(blockers), 4)
        self.assertTrue(all(value is False for value in blockers.values()))

    def test_report_inputs_are_hash_bound(self):
        self.assertEqual(len(self.report["inputs"]), 10)
        for artifact in self.report["inputs"].values():
            path = ROOT / artifact["path"]
            self.assertEqual(
                hashlib.sha256(path.read_bytes()).hexdigest(), artifact["sha256"]
            )

    def test_markdown_states_goal_and_evidence_boundary_plainly(self):
        self.assertIn("四條分開驗證的證據線", self.markdown)
        self.assertIn("不是私人身分複製", self.markdown)
        self.assertIn("4/19", self.markdown)
        self.assertIn("不是人格能力提升", self.markdown)
        self.assertIn("不表示已觀看任何校準事件", self.markdown)


if __name__ == "__main__":
    unittest.main()
