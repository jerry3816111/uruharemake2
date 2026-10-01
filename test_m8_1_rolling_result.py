from __future__ import annotations

import json
from pathlib import Path
import unittest

from longitudinal_human_model.registry import sha256_file


ROOT=Path(__file__).resolve().parent
RESULT=ROOT/"analysis/m8_1_rolling_scaling_parser_remediation_result.json"
LOCK=ROOT/"configs/m8_1_rolling_scaling_result_lock.json"


class FrozenM81RollingResultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result=json.loads(RESULT.read_text())
        cls.lock=json.loads(LOCK.read_text())

    def test_hash_and_complete_engineering_run_are_frozen(self):
        self.assertEqual(self.lock["result_sha256"],sha256_file(RESULT))
        self.assertEqual("complete_hypothesis_run",self.result["status"])
        self.assertTrue(self.result["engineering_gate_pass"])
        self.assertEqual(108,self.result["resources"]["total_model_calls"])

    def test_scientific_failures_are_not_hidden(self):
        checks=self.result["diagnostic_hypothesis_checks"]
        self.assertEqual(1,sum(checks.values()))
        self.assertFalse(self.result["diagnostic_hypotheses_supported"])
        self.assertLess(self.result["metrics"]["OURS_HYBRID"]["top1_accuracy"],self.result["metrics"]["B5_STRUCTURED_HISTORY"]["top1_accuracy"])
        self.assertGreater(self.result["history_scaling_metrics"]["D7_ALL_AVAILABLE"]["negative_log_likelihood"],self.result["history_scaling_metrics"]["D0_PROFILE_ONLY"]["negative_log_likelihood"])

    def test_rolling_instability_and_m7_sign_reversals_are_frozen(self):
        self.assertEqual(1.0,self.result["rolling_metrics"]["E3"]["top1_accuracy"])
        self.assertEqual(.25,self.result["rolling_metrics"]["E4"]["top1_accuracy"])
        for component in ("temporal_dynamics","relationship","preference"):
            self.assertGreater(self.result["ablations"][component]["delta_vs_full"]["negative_log_likelihood"],0)

    def test_parser_amendment_is_bounded_and_visible(self):
        repair=self.result["parser_remediation"]
        self.assertEqual(2,repair["normalization_count"])
        self.assertFalse(repair["prompt_changed"])
        self.assertFalse(repair["data_changed"])
        self.assertFalse(repair["retry_within_run"])


if __name__=="__main__": unittest.main()
