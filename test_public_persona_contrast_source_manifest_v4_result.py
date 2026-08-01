import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REPORT_JSON = (
    ROOT / "reports/public_persona_contrast_source_manifest_v4_audit.json"
)
REPORT_MD = ROOT / "reports/public_persona_contrast_source_manifest_v4_audit.md"
HARNESS_LOCK = (
    ROOT / "configs/public_persona_contrast_source_manifest_v4_harness_lock.json"
)
RESULT_LOCK = (
    ROOT / "configs/public_persona_contrast_source_manifest_v4_result_lock.json"
)


class PublicPersonaContrastSourceManifestV4ResultTests(unittest.TestCase):
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
            "authorize_contrast_event_coding_preregistration_only",
        )
        self.assertEqual(self.report["summary"]["protocol_check_pass_count"], 14)
        self.assertEqual(self.report["summary"]["protocol_check_count"], 14)
        self.assertEqual(self.report["summary"]["formal_readiness_pass_count"], 4)
        self.assertEqual(self.report["summary"]["formal_readiness_check_count"], 19)
        self.assertEqual(self.report["violations"], {})

    def test_actor_topic_matrix_is_complete(self):
        matrix = self.report["actor_topic_matrix"]
        self.assertEqual(len(matrix), 3)
        expected_topics = ["competitive_fps", "fighting_game", "simulation_game"]
        for actor in matrix:
            self.assertEqual(actor["source_count"], 3)
            self.assertEqual(actor["topic_cells"], expected_topics)

    def test_exact_and_broad_matches_remain_separate(self):
        match_strength = self.report["match_strength"]
        self.assertEqual(match_strength["exact_game"]["source_count"], 6)
        self.assertEqual(
            match_strength["exact_game"]["topic_cells"],
            ["competitive_fps", "fighting_game"],
        )
        self.assertEqual(match_strength["broad_family_only"]["source_count"], 3)
        self.assertEqual(
            match_strength["broad_family_only"]["topic_cells"],
            ["simulation_game"],
        )
        self.assertIn(
            "cannot be labeled exact-topic",
            match_strength["broad_family_only"]["claim_boundary"],
        )

    def test_no_behavior_pair_model_score_or_holdout_data_was_created(self):
        summary = self.report["summary"]
        for field in (
            "contrast_behavior_event_count",
            "independently_reviewed_event_count",
            "same_topic_reference_pair_count",
            "model_response_count",
            "persona_score_count",
            "holdout_content_review_count",
            "runtime_change_count",
            "model_call_count",
        ):
            self.assertEqual(summary[field], 0, field)

    def test_authorization_is_next_preregistration_only(self):
        auth = self.report["authorizations"]
        self.assertTrue(auth["contrast_event_coding_preregistration"])
        for field in (
            "contrast_behavior_content_review",
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

    def test_report_inputs_are_hash_bound(self):
        self.assertEqual(len(self.report["inputs"]), 7)
        for artifact in self.report["inputs"].values():
            path = ROOT / artifact["path"]
            self.assertEqual(
                hashlib.sha256(path.read_bytes()).hexdigest(), artifact["sha256"]
            )

    def test_markdown_states_plain_language_evidence_boundary(self):
        self.assertIn("3 人、9 個官方來源", self.markdown)
        self.assertIn("同遊戲", self.markdown)
        self.assertIn("同類型", self.markdown)
        self.assertIn("來源仍不是行為事件", self.markdown)
        self.assertIn("沒有保存標題、字幕、留言、逐字稿、原句", self.markdown)
        self.assertIn("不授權觀看對照內容", self.markdown)


if __name__ == "__main__":
    unittest.main()
