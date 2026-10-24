import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
LOCK = ROOT / "configs/m10_2_behavior_preserving_register_result_lock.json"


class FrozenM102RegisterResultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lock = json.loads(LOCK.read_text())
        cls.result_path = ROOT / cls.lock["result"]["path"]
        cls.result = json.loads(cls.result_path.read_text())

    def test_result_hash_cost_and_human_boundary_are_frozen(self):
        self.assertEqual(hashlib.sha256(self.result_path.read_bytes()).hexdigest(), self.lock["result"]["sha256"])
        self.assertEqual(self.result["resources"]["total_model_calls"], 72)
        self.assertEqual(self.result["resources"]["production_memory_writes"], 0)
        self.assertFalse(self.result["human_preference_supported"])

    def test_surface_gain_and_authority_regression_both_remain_visible(self):
        metrics = self.result["metrics"]
        self.assertEqual(metrics["S0_ONE_PASS"]["visible_contract_pass_rate"], 0.722222)
        self.assertEqual(metrics["S1_REGISTER_REPAIR"]["visible_contract_pass_rate"], 1.0)
        self.assertEqual(metrics["S0_ONE_PASS"]["authority_alignment_rate"], 1.0)
        self.assertEqual(metrics["S1_REGISTER_REPAIR"]["authority_alignment_rate"], 0.944444)
        self.assertEqual(self.result["aligned_to_misaligned_regression_count"], 1)
        self.assertFalse(self.result["all_hypotheses_supported"])

    def test_exact_regression_case_is_frozen(self):
        pair = next(row for row in self.result["pairs"] if row["aligned_to_misaligned_regression"])
        self.assertEqual(pair["case_id"], "R-JA-06")
        rows = [row for row in self.result["rows"] if row["case_id"] == "R-JA-06"]
        decoded = {row["condition"]: row["decoded_behavior"] for row in rows}
        self.assertEqual(decoded["S0_ONE_PASS"], "pause_and_reassess")
        self.assertEqual(decoded["S1_REGISTER_REPAIR"], "defer_commitment")


if __name__ == "__main__":
    unittest.main()
