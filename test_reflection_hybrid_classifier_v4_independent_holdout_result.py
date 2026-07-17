import hashlib
import json
import unittest
from collections import Counter
from pathlib import Path

from reflection_hybrid_classifier_v2_core import analyze_condition
from reflection_hybrid_classifier_v4_core import scorer_gates


ROOT = Path(__file__).resolve().parent
RESULT_LOCK_PATH = (
    ROOT
    / "configs"
    / "reflection_hybrid_classifier_v4_independent_holdout_result_lock.json"
)


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ReflectionHybridClassifierV4IndependentHoldoutResultTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lock = _load(RESULT_LOCK_PATH)
        bindings = cls.lock["artifact_bindings"]
        cls.raw = _load(ROOT / bindings["raw_result"])
        cls.analysis = _load(ROOT / bindings["analysis_json"])
        cls.dataset = _load(ROOT / bindings["dataset"])
        cls.preregistration = _load(ROOT / bindings["preregistration"])
        cls.amendment = _load(ROOT / bindings["protocol_amendment"])

    def test_result_and_every_causal_input_are_hash_bound(self):
        bindings = self.lock["artifact_bindings"]
        for key, expected in bindings.items():
            if not key.endswith("_sha256"):
                continue
            path_key = key.removesuffix("_sha256")
            self.assertIn(path_key, bindings)
            self.assertEqual(_sha256(ROOT / bindings[path_key]), expected, path_key)

    def test_analysis_recomputes_exactly_from_frozen_raw_rows(self):
        recomputed = analyze_condition(
            self.dataset["cases"],
            self.raw["rules_predictions"],
            self.raw["fallback_rows"],
            scorer_gates(self.preregistration, self.amendment),
        )
        self.assertEqual(recomputed, self.raw["gate_snapshot"])
        self.assertEqual(recomputed, self.analysis["matched_result"])

    def test_matched_result_improves_safely_but_fails_capability_gates(self):
        result = self.analysis["matched_result"]
        self.assertEqual(result["rules_correct_count"], 18)
        self.assertEqual(result["rules_accuracy"], 0.5625)
        self.assertEqual(result["hybrid_correct_count"], 24)
        self.assertEqual(result["hybrid_accuracy"], 0.75)
        self.assertEqual(result["accuracy_delta"], 0.1875)
        self.assertEqual(result["newly_correct_count"], 6)
        self.assertEqual(result["regression_count"], 0)
        self.assertEqual(result["critical_false_positive_count"], 0)
        self.assertFalse(result["all_gates_pass"])
        self.assertFalse(result["gate_checks"]["hybrid_correct_count_min"])
        self.assertFalse(result["gate_checks"]["hybrid_accuracy_min"])
        self.assertFalse(result["gate_checks"]["procedural_correct_min"])
        self.assertFalse(result["gate_checks"]["interpretive_correct_min"])

    def test_class_failures_and_missed_cases_are_exact(self):
        result = self.analysis["matched_result"]
        self.assertEqual(
            {
                label: row["correct"]
                for label, row in result["class_metrics"].items()
            },
            {"semantic": 8, "procedural": 5, "interpretive": 3, "none": 8},
        )
        misses = {row["id"] for row in result["rows"] if not row["hybrid_correct"]}
        self.assertEqual(
            misses,
            {
                "fresh_proc_eng_13223930",
                "fresh_proc_jpn_11924316",
                "fresh_proc_jpn_992917",
                "fresh_int_eng_11596055",
                "fresh_int_eng_11570970",
                "fresh_int_eng_9714758",
                "fresh_int_eng_12927409",
                "fresh_int_eng_6359798",
            },
        )

    def test_tool_transport_and_latency_passed(self):
        result = self.analysis["matched_result"]
        self.assertEqual(self.raw["model_calls"], 22)
        self.assertEqual(len(self.raw["fallback_rows"]), 22)
        self.assertEqual(result["parse_success_count"], 22)
        self.assertEqual(result["parse_success_rate"], 1.0)
        self.assertEqual(self.analysis["parse_error_counts"], {})
        self.assertEqual(
            Counter(row["transport_attempts"] for row in self.raw["fallback_rows"]),
            {1: 22},
        )
        self.assertLessEqual(result["median_fallback_wall_seconds"], 3.0)
        self.assertLessEqual(result["warm_p95_fallback_wall_seconds"], 5.0)

    def test_negative_decision_forbids_shadow_runtime_and_retest(self):
        self.assertEqual(
            self.analysis["decision"],
            "freeze_the_negative_result_keep_runtime_typed_reflection_disabled_and_do_not_retest_this_holdout",
        )
        self.assertFalse(
            self.analysis["shadow_integration_preregistration_authorized"]
        )
        self.assertFalse(self.analysis["runtime_memory_write_authorized"])
        self.assertFalse(self.analysis["broad_human_likeness_claim_authorized"])
        self.assertFalse(self.lock["same_holdout_retest_authorized"])
        self.assertFalse(self.lock["same_holdout_prompt_tuning_authorized"])
        self.assertFalse(self.lock["runtime_memory_write_authorized"])

    def test_run_provenance_is_complete(self):
        self.assertEqual(self.raw["runner_commit"], self.lock["runner_commit"])
        self.assertEqual(self.raw["runner_branch"], "main")
        self.assertIsNotNone(self.raw["completed_at"])
        self.assertFalse(self.raw["gold_label_passed_to_model"])
        self.assertFalse(self.raw["runtime_memory_write_performed"])


if __name__ == "__main__":
    unittest.main()
