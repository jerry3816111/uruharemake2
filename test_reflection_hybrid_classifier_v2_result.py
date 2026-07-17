import hashlib
import json
import unittest
from collections import Counter
from pathlib import Path

import uruha_reflection_runtime as reflection
from reflection_hybrid_classifier_v2_core import analyze_condition


ROOT = Path(__file__).resolve().parent
RESULT_LOCK_PATH = (
    ROOT / "configs" / "reflection_hybrid_classifier_v2_result_lock.json"
)


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ReflectionHybridClassifierV2ResultTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lock = _load(RESULT_LOCK_PATH)
        bindings = cls.lock["artifact_bindings"]
        cls.raw = _load(ROOT / bindings["raw_result"])
        cls.analysis = _load(ROOT / bindings["analysis_json"])
        cls.dataset = _load(ROOT / bindings["dataset"])
        cls.preregistration = _load(ROOT / bindings["preregistration"])

    def test_result_and_frozen_inputs_are_hash_bound(self):
        bindings = self.lock["artifact_bindings"]
        for key, expected in bindings.items():
            if not key.endswith("_sha256"):
                continue
            path_key = key.removesuffix("_sha256")
            self.assertIn(path_key, bindings)
            self.assertEqual(_sha256(ROOT / bindings[path_key]), expected, path_key)

    def test_every_condition_recomputes_exactly_from_frozen_raw_rows(self):
        for condition in self.raw["conditions"]:
            model = condition["model"]
            recomputed = analyze_condition(
                self.dataset["cases"],
                self.raw["rules_predictions"],
                condition["fallback_rows"],
                self.preregistration["success_gates"],
            )
            self.assertEqual(recomputed, condition["gate_snapshot"])
            self.assertEqual(recomputed, self.analysis["analyses"][model])

    def test_model_provenance_and_call_accounting_are_exact(self):
        expected_models = [
            row["model"]
            for row in self.preregistration["model_search"]["ordered_conditions"]
        ]
        tested_models = [row["model"] for row in self.raw["conditions"]]
        self.assertEqual(tested_models, expected_models)
        self.assertEqual(self.analysis["tested_models"], expected_models)
        self.assertEqual(self.raw["runner_branch"], "main")
        self.assertEqual(self.raw["runner_commit"], self.lock["runner_commit"])
        self.assertEqual(self.raw["model_calls"], 80)
        self.assertEqual(self.analysis["model_calls"], 80)
        self.assertTrue(
            all(len(row["fallback_rows"]) == 20 for row in self.raw["conditions"])
        )
        self.assertFalse(self.raw["gold_label_passed_to_model"])
        for frozen in self.preregistration["model_search"]["ordered_conditions"]:
            observed = self.raw["model_inventory"][frozen["model"]]
            self.assertEqual(observed["digest"], frozen["digest"])

    def test_no_model_passed_the_preregistered_gates(self):
        self.assertIsNone(self.raw["selected_model"])
        self.assertIsNone(self.analysis["selected_model"])
        self.assertFalse(self.raw["early_stop_triggered"])
        for model, result in self.analysis["analyses"].items():
            with self.subTest(model=model):
                self.assertEqual(result["rules_correct_count"], 20)
                self.assertEqual(result["hybrid_correct_count"], 20)
                self.assertEqual(result["hybrid_accuracy"], 0.625)
                self.assertEqual(result["newly_correct_count"], 0)
                self.assertEqual(result["regression_count"], 0)
                self.assertEqual(result["critical_false_positive_count"], 0)
                self.assertEqual(result["parse_success_count"], 0)
                self.assertEqual(result["parse_success_rate"], 0.0)
                self.assertFalse(result["all_gates_pass"])
                self.assertTrue(
                    result["gate_checks"]["median_fallback_wall_seconds_max"]
                )
                self.assertTrue(
                    result["gate_checks"]["warm_p95_fallback_wall_seconds_max"]
                )

    def test_contract_failure_diagnostic_is_exact_but_not_rescored(self):
        errors = Counter(
            row["parse_error"]
            for condition in self.raw["conditions"]
            for row in condition["fallback_rows"]
        )
        self.assertEqual(errors, {"invalid_json": 29, "schema_keys": 51})
        self.assertTrue(
            any(
                '"label"' in row["raw_content"]
                for condition in self.raw["conditions"]
                for row in condition["fallback_rows"]
            )
        )
        self.assertFalse(self.lock["post_result_rescore_authorized"])
        self.assertTrue(self.lock["same_data_diagnostic_reuse_authorized"])

    def test_failed_pilot_does_not_authorize_runtime_advancement(self):
        self.assertEqual(
            self.analysis["decision"],
            "reject_local_semantic_fallback_and_reconsider_classifier_architecture",
        )
        self.assertFalse(self.analysis["runtime_memory_write_authorized"])
        self.assertFalse(self.lock["runtime_memory_write_authorized"])
        self.assertFalse(self.lock["fresh_holdout_authorized"])
        self.assertFalse(self.lock["broad_human_likeness_claim_authorized"])
        self.assertFalse(reflection.typed_reflection_runtime_enabled({}))


if __name__ == "__main__":
    unittest.main()
