import json
import unittest
from pathlib import Path

from run_rightbrain_role_ladder_v34 import _selected_cases


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "rightbrain_role_specialization_v34_preregistration.json"
DATASET_PATH = ROOT / "datasets" / "rightbrain_qwen35_migration_v33_holdout.json"


class RightBrainRoleSpecializationV34Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        cls.dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))

    def test_preregistration_freezes_role_separation_before_inference(self):
        self.assertEqual(
            self.config["status"],
            "preregistered_before_v34_pilot_inference_and_before_fresh_confirmation_holdout",
        )
        contract = self.config["role_contract"]
        self.assertIn("approved semantic speech plan", contract["rightbrain"])
        self.assertIn("allowlisted", contract["action_planner"])
        self.assertIn("Deny ambiguous", contract["action_validator"])

    def test_ladder_contains_lower_bound_candidates_and_references(self):
        conditions = self.config["development_pilot"]["conditions"]
        self.assertEqual(len(conditions), 5)
        self.assertEqual(conditions["qwen3_5_0_8b_lower_bound"]["role"], "lower_bound_not_presumed_deployable")
        self.assertEqual(conditions["qwen3_5_9b_upper_reference"]["role"], "high_capacity_reference")
        self.assertEqual(len({row["digest"] for row in conditions.values()}), 5)

    def test_development_cases_cover_each_category_once(self):
        cases = _selected_cases(self.config, self.dataset)
        self.assertEqual(len(cases), 12)
        self.assertEqual(len({case["category"] for case in cases}), 12)

    def test_development_data_cannot_authorize_runtime(self):
        self.assertFalse(self.config["runtime_change_authorized"])
        self.assertFalse(self.config["persona_training_authorized"])
        self.assertFalse(self.config["human_likeness_claim_authorized"])
        self.assertIn("retired as confirmation evidence", self.config["development_pilot"]["reuse_disclosure"])


if __name__ == "__main__":
    unittest.main()
