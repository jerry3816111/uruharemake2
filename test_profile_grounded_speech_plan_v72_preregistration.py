import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PREREG = ROOT / "configs/profile_grounded_speech_plan_v72_preregistration.json"


class ProfileGroundedSpeechPlanV72PreregistrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(PREREG.read_text(encoding="utf-8"))

    def test_scope_is_fresh_balanced_and_bounded(self):
        dataset = self.data["planned_dataset"]
        self.assertEqual(dataset["case_count"], 24)
        self.assertEqual(dataset["scenario_family_count"], 6)
        self.assertEqual(dataset["memory_relevant_case_count"], 16)
        self.assertEqual(dataset["memory_irrelevant_case_count"], 8)
        self.assertEqual(dataset["abstention_case_count"], 4)
        self.assertTrue(dataset["must_exclude_v71_inputs_and_values"])
        self.assertFalse(dataset["official_benchmark_items"])

    def test_primary_comparison_changes_only_relation_slot(self):
        self.assertIn("value_relation_plan_treatment", self.data["primary_causal_comparison"])
        self.assertIn("value_only_plan_control", self.data["primary_causal_comparison"])
        self.assertEqual(
            self.data["only_changed_component_for_primary_comparison"],
            "whether the typed speech plan contains and verifies the fact relation; selected memory, value slot, answerability, selector, full-chat pipeline, RightBrain mode, and scorer remain identical",
        )

    def test_preregistration_does_not_authorize_implementation_or_inference(self):
        authorization = self.data["authorizations"]
        self.assertTrue(authorization["dataset_construction"])
        self.assertTrue(authorization["dataset_audit"])
        for key in (
            "bridge_implementation",
            "harness_implementation",
            "formal_inference",
            "temporary_chroma_access",
            "production_database_access",
            "runtime_change",
            "answer_use",
        ):
            self.assertFalse(authorization[key], key)

    def test_failure_modes_and_cost_are_separately_gateable(self):
        gates = self.data["ability_success_gates"]
        self.assertEqual(gates["polarity_error_count_max"], 0)
        self.assertEqual(gates["structural_label_leak_count_max"], 0)
        self.assertGreaterEqual(gates["newly_passed_vs_current_pipeline_min"], 6)
        costs = self.data["local_cost_gates"]
        self.assertGreaterEqual(costs["leftbrain_model_calls_reduction_vs_current_min"], 8)
        self.assertLessEqual(costs["supported_memory_turn_p95_seconds_max"], 8.0)


if __name__ == "__main__":
    unittest.main()
