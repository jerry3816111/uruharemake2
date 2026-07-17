import hashlib
import json
import unittest
from collections import Counter
from pathlib import Path

import uruha_reflection_runtime as reflection
from reflection_hybrid_classifier_v2_core import (
    analyze_condition,
    select_smallest_passing,
)


ROOT = Path(__file__).resolve().parent
RESULT_LOCK_PATH = (
    ROOT / "configs" / "reflection_hybrid_classifier_v3_tool_carrier_result_lock.json"
)


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ReflectionHybridClassifierV3ToolCarrierResultTest(unittest.TestCase):
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
        analyses = {}
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
            analyses[model] = recomputed
        selected = select_smallest_passing(
            self.preregistration["model_search"]["ordered_conditions"], analyses
        )
        self.assertEqual(selected, "qwen3.5:4b")

    def test_model_search_stopped_at_the_smallest_passing_model(self):
        self.assertEqual(
            [row["model"] for row in self.raw["conditions"]],
            ["qwen3.5:0.8b", "qwen3.5:2b", "qwen3.5:4b"],
        )
        self.assertEqual(self.raw["selected_model"], "qwen3.5:4b")
        self.assertEqual(self.analysis["selected_model"], "qwen3.5:4b")
        self.assertTrue(self.raw["early_stop_triggered"])
        self.assertEqual(self.raw["model_calls"], 60)
        self.assertEqual(self.analysis["model_calls"], 60)
        self.assertFalse(self.raw["gold_label_passed_to_model"])
        self.assertEqual(self.raw["runner_branch"], "main")
        self.assertEqual(self.raw["runner_commit"], self.lock["runner_commit"])

    def test_smaller_models_failed_and_4b_passed_every_gate(self):
        analyses = self.analysis["analyses"]
        self.assertFalse(analyses["qwen3.5:0.8b"]["all_gates_pass"])
        self.assertFalse(analyses["qwen3.5:2b"]["all_gates_pass"])
        selected = analyses["qwen3.5:4b"]
        self.assertTrue(selected["all_gates_pass"])
        self.assertTrue(all(selected["gate_checks"].values()))
        self.assertEqual(selected["hybrid_correct_count"], 29)
        self.assertEqual(selected["hybrid_accuracy"], 0.9062)
        self.assertEqual(selected["newly_correct_count"], 9)
        self.assertEqual(selected["regression_count"], 0)
        self.assertEqual(selected["critical_false_positive_count"], 0)
        self.assertEqual(selected["parse_success_rate"], 1.0)
        self.assertEqual(
            {
                label: row["correct"]
                for label, row in selected["class_metrics"].items()
            },
            {"semantic": 8, "procedural": 6, "interpretive": 7, "none": 8},
        )

    def test_parse_failures_and_remaining_misses_are_exact(self):
        errors = Counter(
            row["parse_error"]
            for condition in self.raw["conditions"]
            for row in condition["fallback_rows"]
            if row["parse_error"] is not None
        )
        self.assertEqual(errors, {"missing_tool_calls": 3})
        misses = {
            row["id"]
            for row in self.analysis["analyses"]["qwen3.5:4b"]["rows"]
            if not row["hybrid_correct"]
        }
        self.assertEqual(
            misses,
            {
                "ext_proc_jpn_5962359",
                "ext_proc_cmn_13519695",
                "ext_int_eng_4843024",
            },
        )

    def test_pass_authorizes_only_a_fresh_holdout_not_runtime(self):
        self.assertEqual(
            self.analysis["decision"],
            "authorize_fresh_source_separated_holdout_preregistration_only",
        )
        self.assertTrue(self.lock["fresh_holdout_preregistration_authorized"])
        self.assertFalse(self.lock["same_data_generalization_claim_authorized"])
        self.assertFalse(self.analysis["runtime_memory_write_authorized"])
        self.assertFalse(self.lock["runtime_memory_write_authorized"])
        self.assertFalse(self.lock["broad_human_likeness_claim_authorized"])
        self.assertFalse(reflection.typed_reflection_runtime_enabled({}))


if __name__ == "__main__":
    unittest.main()
