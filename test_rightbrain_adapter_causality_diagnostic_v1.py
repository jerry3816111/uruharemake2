import json
import unittest

import rightbrain_adapter_causality_diagnostic_v1 as diagnostic


class RightBrainAdapterCausalityDiagnosticV1ConstructionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.preregistration = json.loads(
            diagnostic.DEFAULT_PREREGISTRATION.read_text(encoding="utf-8")
        )

    def test_single_causal_variable_is_adapter_enablement(self):
        self.assertEqual(
            self.preregistration["single_changed_variable"],
            "rightbrain_surface_adapter_enabled",
        )
        conditions = self.preregistration["model_conditions"]
        self.assertEqual(conditions[0]["base_model"], conditions[1]["base_model"])
        self.assertIsNone(conditions[0]["adapter"])
        self.assertEqual(
            conditions[1]["adapter"],
            "uruha_rightbrain_plan_sft_lora_v10_expanded_rejection_v1",
        )

    def test_prior_failure_is_disclosed_as_observed_development_evidence(self):
        known = self.preregistration["known_before_preregistration"]
        self.assertTrue(known["previous_result_was_observed"])
        self.assertEqual(known["v10_previous_strict_valid_generation_count"], 2)
        self.assertFalse(known["formal_holdout_claim_allowed"])

    def test_twenty_generations_and_controls_are_frozen(self):
        frozen = self.preregistration["frozen_inputs"]
        self.assertEqual(frozen["total_generation_count"], 20)
        self.assertEqual(frozen["prompt_allocation_budget_tokens"], 640)
        self.assertEqual(frozen["candidate_count"], 1)
        self.assertFalse(frozen["repair_enabled"])
        self.assertEqual(
            frozen["model_execution_order"],
            [diagnostic.BASE_ONLY, diagnostic.V10_ADAPTER],
        )

    def test_classification_boundaries_are_mutually_ordered(self):
        self.assertEqual(
            diagnostic.classify_diagnostic(8, 2),
            "adapter_is_primary_regression_source",
        )
        self.assertEqual(
            diagnostic.classify_diagnostic(2, 8),
            "base_model_is_primary_regression_source",
        )
        self.assertEqual(
            diagnostic.classify_diagnostic(3, 2),
            "both_surface_carriers_inadequate",
        )
        self.assertEqual(
            diagnostic.classify_diagnostic(6, 5),
            "inconclusive_small_delta",
        )

    def test_no_persona_or_production_claim_is_preregistered(self):
        boundary = " ".join(self.preregistration["non_authorizations"])
        self.assertIn("formal persona similarity claim", boundary)
        self.assertIn("production default change", boundary)
        self.assertIn("human blind persona rating", boundary)


if __name__ == "__main__":
    unittest.main()
