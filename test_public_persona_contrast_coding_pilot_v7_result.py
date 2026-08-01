import hashlib
import json
import unittest
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REPORT_JSON = (
    ROOT / "reports/public_persona_contrast_coding_pilot_v7_construction.json"
)
REPORT_MD = ROOT / "reports/public_persona_contrast_coding_pilot_v7_construction.md"
PILOT_FRAME = ROOT / "datasets/public_persona_contrast_coding_pilot_frame_v7.json"
HARNESS_LOCK = (
    ROOT / "configs/public_persona_contrast_coding_pilot_v7_harness_lock.json"
)
RESULT_LOCK = (
    ROOT / "configs/public_persona_contrast_coding_pilot_v7_result_lock.json"
)


class PublicPersonaContrastCodingPilotV7ResultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = json.loads(REPORT_JSON.read_text(encoding="utf-8"))
        cls.markdown = REPORT_MD.read_text(encoding="utf-8")
        cls.frame = json.loads(PILOT_FRAME.read_text(encoding="utf-8"))
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
            "authorize_two_human_18_slot_codebook_pilot_only",
        )
        self.assertEqual(self.report["summary"]["check_pass_count"], 9)
        self.assertEqual(self.report["summary"]["check_count"], 9)
        self.assertEqual(self.report["violations"], [])

    def test_frame_is_balanced_and_still_contains_zero_observation_data(self):
        slots = self.frame["sampling_slots"]
        self.assertEqual(len(slots), 18)
        source_counts = Counter(row["source_id"] for row in slots)
        self.assertEqual(len(source_counts), 9)
        self.assertEqual(set(source_counts.values()), {2})
        half_counts = Counter(
            (row["source_id"], row["pilot_half"]) for row in slots
        )
        self.assertEqual(len(half_counts), 18)
        self.assertEqual(set(half_counts.values()), {1})
        for field, expected in self.frame["current_counts"].items():
            self.assertEqual(expected, 18 if field == "pilot_sampling_slot_count" else 0)

    def test_authorization_is_human_codebook_pilot_only(self):
        authorization = self.report["authorizations"]
        self.assertTrue(authorization["two_human_18_slot_codebook_pilot"])
        self.assertEqual(authorization["maximum_human_coder_count"], 2)
        self.assertEqual(authorization["maximum_slot_count_per_coder"], 18)
        for field in (
            "full_90_slot_coding",
            "aggregate_behavior_profile",
            "persona_similarity_comparison",
            "model_execution",
            "target_calibration_behavior_coding",
            "sealed_holdout_unsealing",
            "model_training",
            "public_persona_fidelity_claim",
        ):
            self.assertFalse(authorization[field], field)

    def test_all_human_content_model_score_and_holdout_counts_are_zero(self):
        summary = self.report["summary"]
        for field in (
            "private_ledger_count",
            "content_reviewed_source_count",
            "selected_event_count",
            "coded_event_count",
            "human_coder_count",
            "model_output_count",
            "persona_score_count",
            "holdout_content_review_count",
            "model_call_count",
        ):
            self.assertEqual(summary[field], 0, field)

    def test_markdown_states_reason_scope_and_evidence_boundary(self):
        for phrase in (
            "為什麼不是直接做 90 格",
            "每位 18 格",
            "兩人是否能一致理解 codebook",
            "雜湊凍結的中文操作手冊",
            "不含人物答案",
            "人格分數",
            "不表示任何真人已編碼",
            "不表示可靠度合格",
        ):
            self.assertIn(phrase, self.markdown)


if __name__ == "__main__":
    unittest.main()
