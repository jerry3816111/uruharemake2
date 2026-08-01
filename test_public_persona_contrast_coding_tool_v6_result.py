import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REPORT_JSON = ROOT / "reports/public_persona_contrast_coding_tool_v6_construction.json"
REPORT_MD = ROOT / "reports/public_persona_contrast_coding_tool_v6_construction.md"
HARNESS_LOCK = (
    ROOT / "configs/public_persona_contrast_coding_tool_v6_harness_lock.json"
)
RESULT_LOCK = (
    ROOT / "configs/public_persona_contrast_coding_tool_v6_result_lock.json"
)


class PublicPersonaContrastCodingToolV6ResultTests(unittest.TestCase):
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

    def test_construction_passes_with_exact_check_count(self):
        self.assertTrue(self.report["construction_passed"])
        self.assertEqual(
            self.report["decision"],
            "authorize_local_two_coder_tool_use_for_v5_bounded_manual_coding_only",
        )
        self.assertEqual(self.report["summary"]["check_pass_count"], 10)
        self.assertEqual(self.report["summary"]["check_count"], 10)
        self.assertEqual(self.report["violations"], [])

    def test_all_human_content_model_score_and_holdout_counts_are_zero(self):
        summary = self.report["summary"]
        for field in (
            "private_ledger_count",
            "content_reviewed_source_count",
            "selected_event_count",
            "coded_event_count",
            "model_output_count",
            "persona_score_count",
            "holdout_content_review_count",
            "model_call_count",
        ):
            self.assertEqual(summary[field], 0, field)

    def test_authorization_is_local_tool_use_only(self):
        auth = self.report["authorizations"]
        self.assertTrue(auth["restricted_local_two_coder_tool_use"])
        self.assertEqual(auth["maximum_coder_count"], 2)
        self.assertEqual(auth["maximum_sampling_slot_count_per_coder"], 90)
        for field in (
            "behavior_content_review_outside_private_ledger",
            "model_execution",
            "runtime_change",
            "prompt_change",
            "memory_change",
            "model_training",
            "target_calibration_behavior_coding",
            "sealed_holdout_unsealing",
            "formal_persona_scoring",
            "public_persona_fidelity_claim",
        ):
            self.assertFalse(auth[field], field)

    def test_limitations_are_not_overclaimed(self):
        limitations = self.report["limitations"]
        self.assertFalse(limitations["copied_quote_detection_is_automatic"])
        self.assertTrue(limitations["paraphrase_boundary_depends_on_coder_attestation"])
        self.assertFalse(limitations["actor_identity_blinding_is_feasible"])
        self.assertFalse(limitations["reliability_pass_is_persona_similarity"])

    def test_report_inputs_are_hash_bound(self):
        self.assertEqual(len(self.report["inputs"]), 6)
        for artifact in self.report["inputs"].values():
            path = ROOT / artifact["path"]
            self.assertEqual(
                hashlib.sha256(path.read_bytes()).hexdigest(), artifact["sha256"]
            )

    def test_markdown_states_separation_zero_data_and_human_limitation(self):
        for phrase in (
            "編碼者 A 私有帳本",
            "編碼者 B 私有帳本",
            "目前仍是零資料",
            "無法自動判斷文字是否偷偷照抄原句",
            "不嵌入、不下載",
        ):
            self.assertIn(phrase, self.markdown)


if __name__ == "__main__":
    unittest.main()
