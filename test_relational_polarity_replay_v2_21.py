import unittest

import run_v2_21_relational_polarity_replay as v221


class RelationalPolarityReplayV221Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.case = v221.load_json(v221.CASE_PATH)
        cls.prereg = v221.load_json(v221.PREREG_PATH)
        cls.raw = v221.load_json(v221.V219_RAW_PATH)

    def test_summary_interface_is_complete_before_generation(self):
        result = v221.validate_design(self.case, self.prereg, self.raw)
        self.assertTrue(result["passed"], result["errors"])
        self.assertTrue(result["summary_interface_keys_complete"])

    def test_v220_failed_raw_is_not_present(self):
        self.assertFalse(v221.v220.RAW_PATH.exists())

    def test_lock_binds_frozen_baselines_runtime_and_both_runner_layers(self):
        artifacts = v221.build_lock()["artifacts"]
        self.assertIn("v2_19_frozen_raw", artifacts)
        self.assertIn("reused_v2_20_runner", artifacts)
        self.assertIn("runtime", artifacts)
        self.assertIn("runner_tests", artifacts)


if __name__ == "__main__":
    unittest.main()
