import ast
import json
import unittest
from pathlib import Path

import public_persona_contract_v3 as public_contract
import uruha_persona_policy as persona_policy
from persona_policy_local_model_pilot_v1 import (
    DEFAULT_CASES,
    DEFAULT_PREREGISTRATION,
    EXPERIMENT_ID,
    PROVIDERS,
)


class PersonaPolicyLocalModelPilotV1ConstructionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.preregistration = json.loads(DEFAULT_PREREGISTRATION.read_text(encoding="utf-8"))
        cls.bundle = json.loads(DEFAULT_CASES.read_text(encoding="utf-8"))
        cls.cases = cls.bundle["cases"]

    def test_experiment_and_model_contract_are_frozen(self):
        self.assertEqual(self.preregistration["experiment_id"], EXPERIMENT_ID)
        model = self.preregistration["model_contract"]
        self.assertEqual(model["base_model"], "Qwen/Qwen2.5-7B-Instruct")
        self.assertEqual(model["candidate_count"], 1)
        self.assertFalse(model["repair_enabled"])
        self.assertEqual(model["prompt_allocation_budget_tokens"], 640)
        self.assertTrue(model["local_only"])
        self.assertFalse(model["paid_cloud_inference_allowed"])

    def test_cases_are_five_unique_source_independent_open_ended_items(self):
        self.assertEqual(len(self.cases), 5)
        self.assertEqual(len({case["case_id"] for case in self.cases}), 5)
        self.assertTrue(self.bundle["dataset_kind"].startswith("source_independent"))
        self.assertFalse(self.bundle["contains_benchmark_items"])
        self.assertFalse(self.bundle["contains_target_utterances"])
        self.assertFalse(self.bundle["contains_expected_replies"])
        self.assertNotIn("expected_reply", json.dumps(self.bundle, ensure_ascii=False))
        self.assertNotIn("correct_answer", json.dumps(self.bundle, ensure_ascii=False))

    def test_each_public_context_is_covered_once(self):
        contexts = [case["context"] for case in self.cases]
        self.assertEqual(set(contexts), set(public_contract.POLICIES))
        self.assertEqual(len(contexts), len(set(contexts)))

    def test_only_provider_changes_within_each_pair(self):
        for case in self.cases:
            self.assertEqual(set(case["condition_order"]), set(PROVIDERS))
            self.assertEqual(len(case["condition_order"]), 2)
            logic = case["logic"]
            self.assertTrue(logic["core_message_jp"])
            self.assertTrue(logic["required_marker_groups"])
            self.assertNotIn("provider_id", logic)

    def test_execution_order_alternates(self):
        first_conditions = [case["condition_order"][0] for case in self.cases]
        self.assertEqual(
            first_conditions,
            [
                persona_policy.TARGET_PROVIDER,
                persona_policy.NEUTRAL_PROVIDER,
                persona_policy.TARGET_PROVIDER,
                persona_policy.NEUTRAL_PROVIDER,
                persona_policy.TARGET_PROVIDER,
            ],
        )

    def test_success_does_not_authorize_persona_claim_or_runtime(self):
        authorizations = self.preregistration["authorizations_on_pass"]
        self.assertTrue(authorizations["build_blinded_policy_direction_coding_bundle"])
        for field in (
            "formal_persona_similarity_claim",
            "production_default_enablement",
            "model_training",
            "sealed_holdout_unsealing",
            "public_impersonation",
        ):
            self.assertFalse(authorizations[field], field)

    def test_harness_has_no_remote_or_training_call(self):
        import persona_policy_local_model_pilot_v1 as pilot

        tree = ast.parse(Path(pilot.__file__).read_text(encoding="utf-8"))
        calls = {
            node.func.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        }
        self.assertNotIn("chat", calls)
        self.assertNotIn("fit", calls)
        self.assertNotIn("backward", calls)


if __name__ == "__main__":
    unittest.main()
