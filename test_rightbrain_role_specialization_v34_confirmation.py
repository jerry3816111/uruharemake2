import hashlib
import json
import unittest
from collections import Counter
from pathlib import Path

from build_rightbrain_role_specialization_v34_confirmation import build_dataset


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "rightbrain_role_specialization_v34_confirmation_preregistration.json"
DATASET_PATH = ROOT / "datasets" / "rightbrain_role_specialization_v34_confirmation.json"
POLICY_PATH = ROOT / "vrm_action_policy_v34.py"


class RightBrainRoleSpecializationV34ConfirmationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        cls.dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))

    def test_preregistration_precedes_dataset_authoring(self):
        self.assertEqual(
            self.config["status"],
            "preregistered_before_fresh_confirmation_dataset_authoring_and_inference",
        )
        self.assertEqual(
            self.dataset["authoring_parent_commit"],
            "8af3850f590eb020acf81e2a2d83d301156005e6",
        )
        self.assertEqual(
            self.dataset["preregistration_sha256"],
            hashlib.sha256(CONFIG_PATH.read_bytes()).hexdigest(),
        )
        self.assertEqual(self.dataset["source_separation"]["formal_model_calls_before_dataset_commit"], 0)

    def test_fresh_case_accounting(self):
        right = Counter(case["category"] for case in self.dataset["rightbrain_cases"])
        action = Counter(case["family"] for case in self.dataset["action_cases"])
        self.assertEqual(len(self.dataset["rightbrain_cases"]), 24)
        self.assertEqual(len(right), 12)
        self.assertEqual(set(right.values()), {2})
        self.assertEqual(len(self.dataset["action_cases"]), 36)
        self.assertEqual(len(action), 6)
        self.assertEqual(set(action.values()), {6})
        self.assertEqual(self.dataset["accounting"]["prior_exact_input_overlap"], 0)

    def test_dataset_is_deterministically_rebuildable(self):
        rebuilt = build_dataset()
        self.assertEqual(rebuilt, self.dataset)

    def test_action_policy_is_the_frozen_development_policy(self):
        self.assertEqual(
            hashlib.sha256(POLICY_PATH.read_bytes()).hexdigest(),
            self.config["known_development_results"]["action_validator"]["policy_sha256"],
        )

    def test_confirmation_contains_unseen_colloquial_action_wording(self):
        text = "\n".join(case["user_input"] for case in self.dataset["action_cases"])
        self.assertIn("にこっとして", text)
        self.assertIn("目線をこっちにちょうだい", text)
        self.assertIn("首を縦に動かして", text)

    def test_runtime_and_identity_claims_remain_locked(self):
        self.assertFalse(self.config["runtime_change_authorized"])
        self.assertFalse(self.config["persona_claim_authorized"])
        self.assertFalse(self.config["human_likeness_claim_authorized"])


if __name__ == "__main__":
    unittest.main()
