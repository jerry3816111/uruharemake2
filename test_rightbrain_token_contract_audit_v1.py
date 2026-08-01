import unittest

import audit_rightbrain_token_contract_v1 as audit


class RightBrainTokenContractAuditV1Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = audit.audit()

    def test_source_contract_is_valid(self):
        self.assertTrue(all(self.result["checks"].values()), self.result["checks"])
        self.assertEqual(self.result["treatment"]["row_count"], 80)
        self.assertEqual(self.result["control"]["row_count"], 80)

    def test_current_800_token_contract_does_not_truncate(self):
        self.assertEqual(self.result["current_fixed_allocation"], 800)
        self.assertEqual(self.result["treatment"]["rows_exceeding_current_allocation"], 0)
        self.assertEqual(self.result["control"]["rows_exceeding_current_allocation"], 0)

    def test_lossless_fixed_reduction_is_only_three_point_five_percent(self):
        lossless = self.result["lossless_fixed_allocation"]
        self.assertEqual(lossless["tokens"], 772)
        self.assertEqual(lossless["token_slots_reduced_per_row"], 28)
        self.assertAlmostEqual(lossless["relative_slot_reduction"], 0.035)

    def test_result_does_not_authorize_training_or_persona_claims(self):
        decision = self.result["decision"]
        self.assertEqual(decision["outcome"], "fixed_800_contract_is_not_materially_oversized")
        self.assertFalse(decision["authorize_training"])
        self.assertFalse(decision["authorize_runtime_change"])
        self.assertFalse(decision["authorize_persona_claim"])


if __name__ == "__main__":
    unittest.main()
