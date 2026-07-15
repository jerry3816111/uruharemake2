import json
import unittest
from pathlib import Path

from run_rightbrain_role_specialization_v34_confirmation import (
    BASE_RIGHTBRAIN_CONDITIONS,
    _rightbrain_options,
)


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "rightbrain_role_specialization_v34_confirmation_preregistration.json"


class RunRightBrainRoleSpecializationV34ConfirmationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))

    def test_single_conditions_are_generated_once_and_guarded_is_derived(self):
        self.assertEqual(
            BASE_RIGHTBRAIN_CONDITIONS,
            (
                "qwen2_5_7b_single_reference",
                "qwen3_5_9b_single_upper_reference",
                "qwen3_5_4b_single_ablation",
            ),
        )
        self.assertIn("qwen3_5_4b_guarded_candidate", self.config["rightbrain_conditions"])

    def test_retry_changes_only_frozen_sampling_and_seed_offset(self):
        first = _rightbrain_options(self.config, 20260718, retry=False)
        retry = _rightbrain_options(self.config, 20260718, retry=True)
        self.assertEqual(first["num_ctx"], retry["num_ctx"])
        self.assertEqual(first["num_predict"], retry["num_predict"])
        self.assertLess(retry["temperature"], first["temperature"])
        self.assertEqual(retry["seed"] - first["seed"], 100000)

    def test_confirmation_does_not_authorize_production_or_persona(self):
        self.assertFalse(self.config["runtime_change_authorized"])
        self.assertFalse(self.config["persona_claim_authorized"])
        self.assertFalse(self.config["human_likeness_claim_authorized"])


if __name__ == "__main__":
    unittest.main()
