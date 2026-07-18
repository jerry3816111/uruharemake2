import hashlib
import json
import unittest
from pathlib import Path

import audit_cognitive_plan_decomposition_v66_dataset as audit_module


ROOT = Path(__file__).resolve().parent


class CognitivePlanDecompositionV66DatasetTests(unittest.TestCase):
    def test_audit_passes_with_96_exact_fields_per_condition(self):
        audit = audit_module.build_audit()
        self.assertTrue(audit["passed"], audit["failures"])
        self.assertEqual(audit["counts"]["case_count"], 12)
        self.assertEqual(audit["counts"]["scenario_family_count"], 6)
        self.assertEqual(audit["counts"]["exact_scored_field_count_per_condition"], 96)

    def test_gold_is_separate_and_memory_is_fully_partitioned(self):
        dataset = json.loads((ROOT / "datasets/cognitive_plan_decomposition_v66.json").read_text(encoding="utf-8"))
        for case in dataset["cases"]:
            self.assertNotIn("expected", case["planning_packet"])
            memory_ids = {row["id"] for row in case["planning_packet"]["memory_records"]}
            expected = case["expected"]
            active = set(expected["active_memory_ids"])
            suppressed = set(expected["suppressed_memory_ids"])
            self.assertFalse(active & suppressed)
            self.assertEqual(active | suppressed, memory_ids)
        self.assertFalse(dataset["official_benchmark_items"])

    def test_primary_comparison_holds_model_and_call_count_constant(self):
        prereg = json.loads((ROOT / "configs/cognitive_plan_decomposition_v66_preregistration.json").read_text(encoding="utf-8"))
        conditions = prereg["conditions"]
        self.assertEqual(conditions["two_pass_full_plan_control"]["scored_calls_per_case"], 2)
        self.assertEqual(conditions["two_stage_responsibility_decomposition"]["scored_calls_per_case"], 2)
        self.assertEqual(prereg["model"]["ollama_tag"], "qwen3.5:4b")

    def test_closure_binds_inputs_and_forbids_inference(self):
        closure = json.loads((ROOT / "configs/cognitive_plan_decomposition_v66_dataset_closure.json").read_text(encoding="utf-8"))
        paths = {
            "preregistration": "configs/cognitive_plan_decomposition_v66_preregistration.json",
            "dataset": "datasets/cognitive_plan_decomposition_v66.json",
        }
        for name, relative in paths.items():
            self.assertEqual(
                closure["frozen_artifacts"][name],
                hashlib.sha256((ROOT / relative).read_bytes()).hexdigest(),
            )
        self.assertFalse(closure["authorizations"]["model_inference"])


if __name__ == "__main__":
    unittest.main()
