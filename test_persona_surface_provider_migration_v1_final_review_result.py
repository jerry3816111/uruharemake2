import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
LOCK = ROOT / "configs/persona_surface_provider_migration_v1_result_lock.json"
FINAL = ROOT / "reports/persona_surface_provider_migration_v1_final_review.json"
FINAL_MD = ROOT / "reports/persona_surface_provider_migration_v1_final_review.md"


class PersonaSurfaceProviderMigrationV1FinalReviewTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lock = json.loads(LOCK.read_text(encoding="utf-8"))
        cls.final = json.loads(FINAL.read_text(encoding="utf-8"))

    def test_final_review_authorizes_only_merge_and_fresh_pilot(self):
        self.assertEqual(self.final["status"], "final_review_passed")
        self.assertTrue(self.final["authorizations"]["merge_persona_surface_provider_migration_v1"])
        self.assertTrue(self.final["authorizations"]["fresh_local_model_target_vs_neutral_surface_pilot"])
        for field in (
            "formal_persona_similarity_evaluation",
            "sealed_holdout_unsealing",
            "human_blind_rating",
            "model_training",
            "production_default_enablement",
            "public_persona_fidelity_claim",
            "private_person_copy_claim",
        ):
            self.assertFalse(self.final["authorizations"][field], field)

    def test_final_review_matches_locked_formal_result(self):
        locked = self.lock["formal_result"]
        final = self.final["formal_result"]
        for field in (
            "structured_success_case_count",
            "structured_failed_closed_case_count",
            "structured_legacy_fixed_surface_access_count",
            "structured_reachable_fixed_family_entry_count",
            "legacy_runtime_mismatch_count",
            "actual_local_generation_call_count",
            "holdout_content_review_count",
            "production_memory_write_count",
            "persona_score_count",
        ):
            self.assertEqual(final[field], locked[field], field)
        self.assertEqual(
            final["known_stale_historical_hash_test_count"],
            locked["known_stale_historical_hash_test_count"],
        )

    def test_markdown_states_the_main_result_and_limit(self):
        markdown = FINAL_MD.read_text(encoding="utf-8")
        self.assertIn("structured 固定回覆存取 | 0", markdown)
        self.assertIn("legacy 輸出不一致 | 0/3", markdown)
        self.assertIn("367 個固定回覆字串尚未刪除", markdown)
        self.assertIn("沒有實際本機模型人格分數", markdown)


if __name__ == "__main__":
    unittest.main()
