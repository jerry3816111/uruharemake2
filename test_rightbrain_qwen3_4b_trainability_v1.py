#!/usr/bin/env python3
"""Regression checks for the Qwen3-4B RightBrain trainability probe."""

import ast
import unittest
from pathlib import Path

import build_rightbrain_qwen3_4b_trainability_v1 as construction


ROOT = Path(__file__).resolve().parent
RUNNER = ROOT / "run_rightbrain_qwen3_4b_trainability_v1.py"


class RightBrainQwen3_4BTrainabilityV1Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.preregistration = construction.load_json(construction.DEFAULT_PREREGISTRATION)

    def test_construction_and_data_boundaries(self):
        report = construction.build_report()
        invariant_checks = {
            key: value for key, value in report["checks"].items() if key != "outputs_absent"
        }
        self.assertTrue(all(invariant_checks.values()), invariant_checks)
        self.assertTrue(report["checks"]["official_model_files_bound"])
        self.assertTrue(report["checks"]["dataset_provenance_safe"])
        self.assertTrue(report["checks"]["full_depth_lora"])
        self.assertEqual(report["actual_row_ids"], ["rb_role_specialization_v1_0064"])

    def test_candidate_contract_is_full_capacity_but_zero_update(self):
        model = self.preregistration["local_model_contract"]
        adapter = self.preregistration["adapter_initialization_contract"]
        probe = self.preregistration["exact_probe"]
        self.assertEqual(model["base_model"], "Qwen/Qwen3-4B-Instruct-2507")
        self.assertEqual(model["snapshot_commit"], "cdbee75f17c01a7cc42f958dc650907174af0554")
        self.assertEqual(model["base_parameter_count"], 4022468096)
        self.assertEqual(model["num_hidden_layers"], 36)
        self.assertEqual(adapter["converted_layers"], 36)
        self.assertEqual(adapter["rank"], 32)
        self.assertEqual(adapter["trainable_parameter_count"], 66060288)
        self.assertEqual(adapter["dropout"], 0.0)
        self.assertEqual(probe["micro_steps"], 1)
        self.assertEqual(probe["gradient_accumulation"], 1)
        self.assertEqual(probe["optimizer_steps"], 0)
        self.assertFalse(probe["gradient_checkpointing"])

    def test_runner_has_backward_measurement_but_no_optimizer_or_generation(self):
        source = RUNNER.read_text(encoding="utf-8")
        tree = ast.parse(source)
        calls = {
            node.func.attr if isinstance(node.func, ast.Attribute) else node.func.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, (ast.Attribute, ast.Name))
        }
        imports = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        }
        self.assertIn("value_and_grad", calls)
        self.assertIn("linear_to_lora_layers", calls)
        self.assertIn("_gradient_measurements", calls)
        self.assertNotIn("grad_checkpoint", calls)
        self.assertNotIn("mlx.optimizers", imports)
        for forbidden in ("Adam", "AdamW", "SGD", "save_weights", "generate"):
            self.assertNotIn(forbidden, source)

    def test_safety_boundaries(self):
        boundaries = self.preregistration["boundaries"]
        for key in (
            "optimizer_instantiation",
            "optimizer_step",
            "gradient_clipping",
            "parameter_mutation",
            "adapter_or_model_save",
            "text_generation",
            "production_runtime_change",
            "persona_similarity_claim",
            "target_person_utterances",
            "benchmark_items",
        ):
            self.assertFalse(boundaries[key], key)

    def test_execution_lock_when_available(self):
        if not construction.DEFAULT_EXECUTION_LOCK.exists():
            self.skipTest("Qwen3-4B execution lock not written")
        lock = construction.load_json(construction.DEFAULT_EXECUTION_LOCK)
        for binding in lock["bindings"]:
            path = Path(binding["path"])
            if binding.get("scope") != "external_local" and not path.is_absolute():
                path = ROOT / path
            self.assertTrue(path.is_file(), str(path))
            self.assertEqual(construction.sha256_file(path), binding["sha256"])
        authorization = lock["authorization"]
        self.assertEqual(authorization["micro_steps_each"], 1)
        self.assertEqual(authorization["optimizer_steps"], 0)
        self.assertFalse(authorization["gradient_checkpointing"])
        self.assertFalse(authorization["production_runtime_change"])

    def test_result_lock_when_available(self):
        result_lock_path = ROOT / self.preregistration["result_paths"]["result_lock"]
        if not result_lock_path.exists():
            self.skipTest("Qwen3-4B result lock not available")
        lock = construction.load_json(result_lock_path)
        for binding in lock["result_bindings"]:
            path = Path(binding["path"])
            if binding.get("scope") != "external_local" and not path.is_absolute():
                path = ROOT / path
            self.assertTrue(path.is_file(), str(path))
            self.assertEqual(construction.sha256_file(path), binding["sha256"])
        self.assertFalse(lock["authorization"]["model_training_in_this_experiment"])
        self.assertFalse(lock["authorization"]["production_runtime_change"])
        self.assertFalse(lock["authorization"]["persona_similarity_claim"])

    def test_result_rejects_persona_training_despite_finite_local_execution(self):
        result_path = ROOT / self.preregistration["result_paths"]["aggregate_json"]
        if not result_path.exists():
            self.skipTest("Qwen3-4B aggregate not available")
        result = construction.load_json(result_path)
        self.assertFalse(result["decision"]["passed"])
        self.assertFalse(result["decision"]["authorize_training_now"])
        self.assertEqual(
            result["decision"]["outcome"],
            "qwen3_4b_candidate_trainability_gate_failed",
        )
        self.assertEqual(
            result["decision"]["authorized_next_step"],
            "reject_qwen3_4b_persona_training_without_new_evidence",
        )
        checks = result["checks"]
        for key in (
            "all_three_repetitions_complete",
            "model_and_adapter_contract_exact_each",
            "token_and_label_hash_exact_each",
            "loss_vectors_exact_across_repetitions",
            "all_losses_and_gradients_finite",
            "trainable_parameters_unchanged",
            "peak_memory_within_limit",
        ):
            self.assertTrue(checks[key], key)
        self.assertFalse(checks["gradient_norm_coefficient_of_variation"])
        self.assertFalse(checks["gradient_norm_max_to_min_ratio"])
        self.assertFalse(checks["minimum_pairwise_group_profile_cosine"])
        measurements = result["measurements"]
        self.assertGreater(measurements["gradient_norm_max_to_min_ratio"], 6.0)
        self.assertFalse(measurements["gradient_hashes_identical"])

        repeats = [
            construction.load_json(
                ROOT / f"{self.preregistration['result_paths']['repeat_prefix']}{repeat}.json"
            )
            for repeat in (1, 2, 3)
        ]
        expected_adapter_hash = self.preregistration["adapter_initialization_contract"][
            "initial_trainable_sha256"
        ]
        self.assertTrue(
            all(row["adapter_initialization"]["sha256"] == expected_adapter_hash for row in repeats)
        )
        profiles = [row["gradient"]["profile"] for row in repeats]
        a_groups = [name for name in profiles[0] if name.endswith(".lora_a")]
        b_groups = [name for name in profiles[0] if name.endswith(".lora_b")]
        self.assertTrue(all(profile[name] == 0 for profile in profiles for name in a_groups))
        self.assertTrue(
            all(
                max(profile[name] for profile in profiles)
                / min(profile[name] for profile in profiles)
                > 5.0
                for name in b_groups
            )
        )


if __name__ == "__main__":
    unittest.main()
