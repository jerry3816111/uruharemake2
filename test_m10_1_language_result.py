import json
import hashlib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
LOCK = ROOT / "configs/m10_1_behavior_authoritative_language_result_lock.json"


class FrozenM101LanguageResultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lock = json.loads(LOCK.read_text())
        cls.result_path = ROOT / cls.lock["result"]["path"]
        cls.result = json.loads(cls.result_path.read_text())

    def test_hash_call_counts_and_human_boundary_are_frozen(self):
        self.assertEqual(
            hashlib.sha256(self.result_path.read_bytes()).hexdigest(),
            self.lock["result"]["sha256"],
        )
        self.assertEqual(self.result["resources"]["total_model_calls"], 144)
        self.assertEqual(self.result["resources"]["production_memory_writes"], 0)
        self.assertFalse(self.result["human_preference_supported"])
        self.assertEqual(self.result["summary_parser_remediation"]["normalization_count"], 6)

    def test_authority_success_does_not_hide_outcome_failure(self):
        metrics = self.result["metrics"]
        self.assertEqual(metrics["L1_PREDICTED_BEHAVIOR"]["authority_alignment_rate"], 0.875)
        self.assertEqual(metrics["L2_ORACLE_BEHAVIOR"]["authority_alignment_rate"], 1.0)
        self.assertLess(
            metrics["L1_PREDICTED_BEHAVIOR"]["outcome_alignment_rate"],
            metrics["L0_DIRECT"]["outcome_alignment_rate"],
        )
        self.assertEqual(metrics["L2_ORACLE_BEHAVIOR"]["outcome_alignment_rate"], 1.0)

    def test_surface_failures_and_prompt_parity_remain_visible(self):
        metrics = self.result["metrics"]
        self.assertEqual(metrics["L1_PREDICTED_BEHAVIOR"]["visible_contract_pass_rate"], 0.4375)
        self.assertEqual(metrics["L2_ORACLE_BEHAVIOR"]["visible_contract_pass_rate"], 0.25)
        self.assertTrue(self.result["hypothesis_checks"]["all_scored_prompt_token_ranges_at_most"])
        self.assertTrue(
            all(row["scored_prompt_token_range"] == 0 for row in self.result["prompt_balance"].values())
        )
        self.assertFalse(self.result["all_hypotheses_supported"])


if __name__ == "__main__":
    unittest.main()
