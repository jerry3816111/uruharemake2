from __future__ import annotations

import json
from pathlib import Path
import unittest

from longitudinal_human_model.registry import sha256_file


ROOT=Path(__file__).resolve().parent; RESULT=ROOT/"analysis/m9_1_second_person_transfer_summary_alias_result.json"; LOCK=ROOT/"configs/m9_1_second_person_transfer_result_lock.json"


class FrozenM91TransferResultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.result=json.loads(RESULT.read_text()); cls.lock=json.loads(LOCK.read_text())

    def test_hash_engineering_and_unchanged_core_are_frozen(self):
        self.assertEqual(self.lock["result_sha256"],sha256_file(RESULT)); self.assertTrue(self.result["engineering_gate_pass"]); self.assertEqual(0,sum(self.result["person_specific_core_mentions"].values())); self.assertEqual(108,self.result["resources"]["total_model_calls"])

    def test_only_parameter_swap_hypothesis_passes(self):
        checks=self.result["transfer_hypothesis_checks"]; self.assertEqual(1,sum(checks.values())); self.assertTrue(checks["parameter_swap_top1_at_least_zero_shot"]); self.assertFalse(self.result["transfer_hypotheses_supported"])

    def test_full_adaptation_degradation_and_baseline_floor_remain_visible(self):
        metrics=self.result["metrics"]; self.assertLess(metrics["MIRA_FULL_ADAPTATION"]["top1_accuracy"],metrics["REN_ZERO_SHOT"]["top1_accuracy"]); self.assertLess(metrics["MIRA_FULL_ADAPTATION"]["top1_accuracy"],metrics["B4_FULL_HISTORY_SUMMARY"]["top1_accuracy"]); self.assertGreater(metrics["MIRA_FULL_ADAPTATION"]["brier_score"],1.0)

    def test_summary_alias_and_rolling_instability_are_frozen(self):
        self.assertEqual(3,self.result["summary_parser_remediation"]["normalization_count"]); self.assertEqual(0.0,self.result["rolling_metrics"]["E1"]["top1_accuracy"]); self.assertEqual(1.0,self.result["rolling_metrics"]["E3"]["top1_accuracy"])


if __name__=="__main__": unittest.main()
