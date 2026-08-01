import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REPORT_JSON = ROOT / "reports/public_persona_contrast_event_coding_v5_audit.json"
REPORT_MD = ROOT / "reports/public_persona_contrast_event_coding_v5_audit.md"
HARNESS_LOCK = (
    ROOT / "configs/public_persona_contrast_event_coding_v5_harness_lock.json"
)
RESULT_LOCK = (
    ROOT / "configs/public_persona_contrast_event_coding_v5_result_lock.json"
)


class PublicPersonaContrastEventCodingV5ResultTests(unittest.TestCase):
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
            "authorize_bounded_manual_contrast_event_coding_only",
        )
        self.assertEqual(self.report["summary"]["protocol_check_pass_count"], 15)
        self.assertEqual(self.report["summary"]["protocol_check_count"], 15)
        self.assertEqual(self.report["summary"]["formal_readiness_pass_count"], 4)
        self.assertEqual(self.report["summary"]["formal_readiness_check_count"], 19)
        self.assertEqual(self.report["violations"], {})

    def test_sampling_frame_is_bounded_and_match_strengths_stay_separate(self):
        summary = self.report["summary"]
        self.assertEqual(summary["contrast_source_count"], 9)
        self.assertEqual(summary["sampling_slot_count"], 90)
        self.assertEqual(summary["exact_game_sampling_slot_count"], 60)
        self.assertEqual(summary["broad_family_sampling_slot_count"], 30)
        self.assertEqual(self.report["sampling_design"]["strata_per_source"], 10)
        self.assertFalse(
            self.report["sampling_design"][
                "replacement_after_no_eligible_or_overlap_blocked_allowed"
            ]
        )

    def test_no_content_event_model_score_or_holdout_data_was_created(self):
        summary = self.report["summary"]
        for field in (
            "content_reviewed_source_count",
            "selected_event_count",
            "coded_event_count",
            "independently_reviewed_event_count",
            "same_topic_reference_pair_count",
            "raw_or_verbatim_record_count",
            "model_output_count",
            "persona_score_count",
            "holdout_content_review_count",
            "model_call_count",
        ):
            self.assertEqual(summary[field], 0, field)

    def test_reliability_gate_is_independent_and_chance_corrected(self):
        gates = self.report["reliability_gates"]
        self.assertEqual(gates["independent_review_fraction_required"], 1.0)
        self.assertTrue(gates["unitizing_reliability_reported_separately"])
        self.assertTrue(gates["nominal_code_krippendorff_alpha_primary"])
        self.assertTrue(gates["percent_agreement_secondary_only"])
        self.assertEqual(gates["nominal_alpha_reliable_min"], 0.8)
        self.assertEqual(gates["nominal_alpha_tentative_min"], 0.667)
        self.assertTrue(gates["below_tentative_alpha_blocks_persona_comparison"])

    def test_authorization_is_manual_coding_only(self):
        auth = self.report["authorizations"]
        self.assertTrue(auth["bounded_manual_contrast_event_coding"])
        self.assertEqual(auth["maximum_source_count"], 9)
        self.assertEqual(auth["maximum_sampling_slot_count"], 90)
        for field in (
            "public_event_level_content_storage",
            "target_calibration_behavior_coding",
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

    def test_report_inputs_and_workspace_guard_are_current(self):
        self.assertEqual(len(self.report["inputs"]), 9)
        for artifact in self.report["inputs"].values():
            path = ROOT / artifact["path"]
            self.assertEqual(
                hashlib.sha256(path.read_bytes()).hexdigest(), artifact["sha256"]
            )
        guard = self.report["workspace_guards"]
        self.assertTrue(guard["private_event_directory_is_gitignored"])
        self.assertNotIn(".gitignore", self.harness["frozen_artifacts"])

    def test_markdown_states_plain_language_method_and_evidence_boundary(self):
        for phrase in (
            "搜尋層不是事件",
            "第一個合格的完整事件",
            "人物身分盲化",
            "內容仍是零",
            "不進 Git",
            "不證明代理像任何人物",
        ):
            self.assertIn(phrase, self.markdown)


if __name__ == "__main__":
    unittest.main()
