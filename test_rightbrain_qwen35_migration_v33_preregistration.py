import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PREREG_PATH = ROOT / "configs" / "rightbrain_qwen35_migration_v33_preregistration.json"


class RightBrainQwen35MigrationV33PreregistrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.prereg = json.loads(PREREG_PATH.read_text(encoding="utf-8"))

    def test_preregistration_precedes_holdout_and_inference(self):
        self.assertEqual(
            self.prereg["status"],
            "preregistered_before_fresh_holdout_authoring_and_formal_inference",
        )
        self.assertTrue(self.prereg["known_before_preregistration"]["screening_is_not_formal_evidence"])

    def test_fresh_holdout_accounting_is_frozen(self):
        holdout = self.prereg["stage_1_design"]["fresh_holdout"]
        self.assertEqual(holdout["rightbrain_category_count"], 12)
        self.assertEqual(holdout["rightbrain_cases_per_category"], 4)
        self.assertEqual(holdout["rightbrain_case_count"], 48)
        self.assertEqual(holdout["action_family_count"], 6)
        self.assertEqual(holdout["action_cases_per_family"], 20)
        self.assertEqual(holdout["action_case_count"], 120)

    def test_local_pc_budget_is_explicit(self):
        environment = self.prereg["frozen_environment"]
        treatment = environment["conditions"]["qwen3_5_9b_quantized_treatment"]
        gate = self.prereg["stage_1_advance_gate"]["requirements"]
        self.assertEqual(environment["hardware"]["unified_memory_bytes"], 32 * 1024**3)
        self.assertLessEqual(treatment["blob_bytes"], gate["model_blob_bytes_at_most"])
        self.assertLessEqual(gate["warm_generation_median_seconds_at_most"], 5.0)

    def test_action_and_speech_paths_remain_separate(self):
        boundary = self.prereg["architecture_boundary"]
        self.assertIn("persona surface formulator", boundary["speech_path"])
        self.assertIn("allowlisted validator", boundary["action_path"])
        self.assertIn("must not directly execute unrestricted functions", boundary["prohibited_shortcut"])

    def test_stage_one_cannot_promote_runtime_or_identity_claim(self):
        gate = self.prereg["stage_1_advance_gate"]
        self.assertFalse(gate["runtime_change_authorized"])
        self.assertFalse(gate["persona_claim_authorized"])
        self.assertFalse(gate["human_likeness_claim_authorized"])
        self.assertEqual(self.prereg["stage_2_identity_policy"]["status"], "not_yet_preregistered")


if __name__ == "__main__":
    unittest.main()
