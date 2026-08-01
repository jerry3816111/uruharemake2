import hashlib
import json
import unittest
from pathlib import Path

import uruha_surface_payload_v2 as surface_payload
from uruha_brain_mac import RIGHT_BRAIN_STRUCTURED_PAYLOAD_MODE


ROOT = Path(__file__).resolve().parent
LOCK = ROOT / "configs/rightbrain_compact_japanese_payload_v1_result_lock.json"
RESULT = ROOT / "reports/rightbrain_compact_japanese_payload_v1_result.json"
FINAL = ROOT / "reports/rightbrain_compact_japanese_payload_v1_final_review.json"
FINAL_MD = ROOT / "reports/rightbrain_compact_japanese_payload_v1_final_review.md"


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class CompactJapanesePayloadResultTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lock = json.loads(LOCK.read_text(encoding="utf-8"))
        cls.result = json.loads(RESULT.read_text(encoding="utf-8"))
        cls.final = json.loads(FINAL.read_text(encoding="utf-8"))

    def test_frozen_artifact_hashes_match(self):
        for artifact in self.lock["frozen_artifacts"].values():
            self.assertEqual(
                sha256_file(ROOT / artifact["path"]),
                artifact["sha256"],
                artifact["path"],
            )

    def test_formal_negative_result_is_preserved(self):
        formal = self.lock["formal_result"]
        self.assertEqual(self.result["status"], "valid_experiment")
        self.assertEqual(
            self.result["classification"],
            "compact_payload_regression",
        )
        self.assertEqual(
            self.result["decision"],
            "revert_compact_serializer_experiment",
        )
        self.assertEqual(formal["legacy_strict_valid_generation_count"], 2)
        self.assertEqual(formal["compact_strict_valid_generation_count"], 1)
        self.assertEqual(formal["strict_valid_delta_compact_minus_legacy"], -1)
        self.assertEqual(self.final["formal_result"], {
            key: formal[key]
            for key in self.final["formal_result"]
        })

    def test_all_control_checks_passed(self):
        self.assertTrue(all(self.result["checks"].values()))
        self.assertTrue(
            all(
                row["controls_equal_except_serialization"]
                and row["prompt_hash_difference_exact"]
                and row["compact_active_tokens_lower_each"]
                for row in self.result["cross_serializer_control_checks"]
            )
        )

    def test_pollution_persisted_without_ascii_prompt_words(self):
        compact_rows = [
            row
            for row in self.result["generations"]
            if row["serializer_id"] == surface_payload.COMPACT_JAPANESE_V2
        ]
        case_four = " ".join(
            row["raw_generation"]
            for row in compact_rows
            if row["case_id"] == "persona_local_pilot_04"
        )
        case_five = " ".join(
            row["raw_generation"]
            for row in compact_rows
            if row["case_id"] == "persona_local_pilot_05"
        )
        self.assertIn("throat", case_four)
        self.assertTrue("游戏" in case_five or "直播" in case_five)

    def test_failed_candidate_is_not_promoted(self):
        self.assertEqual(
            RIGHT_BRAIN_STRUCTURED_PAYLOAD_MODE,
            surface_payload.LEGACY_JSON_V1,
        )
        self.assertFalse(
            self.result["authorizations"]["production_default_enablement"]
        )
        self.assertTrue(
            self.final["decision_execution"]["compact_serializer_not_promoted"]
        )
        for field in (
            "claim_persona_similarity",
            "begin_human_blind_rating",
            "train_on_development_cases",
            "unseal_persona_holdout",
        ):
            self.assertFalse(self.final["authorizations"][field], field)

    def test_markdown_reports_regression_and_scope(self):
        markdown = FINAL_MD.read_text(encoding="utf-8")
        self.assertIn("精簡日文格式退步", markdown)
        self.assertIn("2/10", markdown)
        self.assertIn("1/10", markdown)
        self.assertIn("不是人格相似度分數", markdown)


if __name__ == "__main__":
    unittest.main()
