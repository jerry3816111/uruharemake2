import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
LOCK = ROOT / "configs/persona_policy_token_parity_v1_result_lock.json"
FINAL = ROOT / "reports/persona_policy_token_parity_v1_final_review.json"
FINAL_MD = ROOT / "reports/persona_policy_token_parity_v1_final_review.md"


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class PersonaPolicyTokenParityV1FinalReviewTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lock = json.loads(LOCK.read_text(encoding="utf-8"))
        cls.final = json.loads(FINAL.read_text(encoding="utf-8"))

    def test_frozen_construction_artifact_hashes_match(self):
        for artifact in self.lock["frozen_artifacts"].values():
            self.assertEqual(
                sha256_file(ROOT / artifact["path"]),
                artifact["sha256"],
                artifact["path"],
            )

    def test_final_review_matches_locked_formal_result(self):
        self.assertEqual(self.final["status"], "final_review_passed")
        self.assertEqual(self.final["formal_git_head"], self.lock["formal_git_head"])
        self.assertEqual(self.final["formal_result"], self.lock["formal_result"])

    def test_only_merge_and_fresh_pilot_are_authorized(self):
        authorizations = self.final["authorizations"]
        self.assertTrue(authorizations["merge_persona_policy_token_parity_v1"])
        self.assertTrue(
            authorizations["fresh_local_model_target_vs_neutral_surface_pilot"]
        )
        for field in (
            "formal_persona_similarity_evaluation",
            "sealed_holdout_unsealing",
            "human_blind_rating",
            "model_training",
            "production_default_enablement",
            "public_persona_fidelity_claim",
            "private_person_copy_claim",
        ):
            self.assertFalse(authorizations[field], field)

    def test_active_length_difference_is_not_hidden(self):
        boundary = self.lock["evidence_boundary"]
        self.assertFalse(boundary["active_prompt_length_is_equal"])
        self.assertTrue(boundary["allocated_prompt_length_is_equal"])
        self.assertTrue(
            self.final["review_findings"]["active_token_difference_reported_not_hidden"]
        )

    def test_markdown_states_result_and_limit(self):
        markdown = FINAL_MD.read_text(encoding="utf-8")
        self.assertIn("640／640", markdown)
        self.assertIn("250／250", markdown)
        self.assertIn("有效長度差異仍保留", markdown)
        self.assertIn("尚未產生人格相似度", markdown)


if __name__ == "__main__":
    unittest.main()
