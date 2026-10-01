import unittest

import run_v2_22_stable_relational_source_replay as v222


class StableRelationalSourceReplayV222Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.case = v222.load_json(v222.CASE_PATH)
        cls.prereg = v222.load_json(v222.PREREG_PATH)
        cls.v219_raw = v222.load_json(v222.V219_RAW_PATH)
        cls.v221_raw = v222.load_json(v222.V221_RAW_PATH)

    def test_design_binds_both_frozen_reference_results(self):
        result = v222.validate_design(
            self.case,
            self.prereg,
            self.v219_raw,
            self.v221_raw,
        )
        self.assertTrue(result["passed"], result["errors"])
        self.assertTrue(result["summary_interface_keys_complete"])
        self.assertTrue(result["v2_21_reference_sha256"])

    def test_v221_reference_exposes_denial_without_relation_attribution(self):
        row = v222._lookup(self.v221_raw)[50]
        self.assertIn("聞いてない", row["reply"])
        self.assertNotIn("友達", row["reply"])
        self.assertFalse(row["score"]["relational_false_claim_directly_denied"])

    def test_lock_binds_runtime_and_v219_v221_raw(self):
        artifacts = v222.build_lock()["artifacts"]
        self.assertIn("v2_19_frozen_raw", artifacts)
        self.assertIn("v2_21_frozen_raw", artifacts)
        self.assertIn("runtime", artifacts)


if __name__ == "__main__":
    unittest.main()
