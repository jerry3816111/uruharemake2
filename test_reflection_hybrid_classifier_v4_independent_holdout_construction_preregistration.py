import json
import unittest
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = (
    ROOT
    / "configs"
    / "reflection_hybrid_classifier_v4_independent_holdout_construction_preregistration.json"
)
PRIOR_CONFIG_PATH = (
    ROOT
    / "configs"
    / "reflection_classifier_v1_external_holdout_construction_preregistration.json"
)


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


class ReflectionHybridClassifierV4IndependentHoldoutConstructionPreregistrationTest(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls):
        cls.config = _load(CONFIG_PATH)
        cls.prior = _load(PRIOR_CONFIG_PATH)

    def test_selected_ids_and_balance_are_frozen(self):
        cases = self.config["selected_cases"]
        counts = self.config["fixed_counts"]
        self.assertEqual(len(cases), counts["case_count"])
        self.assertEqual(len({case["id"] for case in cases}), len(cases))
        self.assertEqual(len({case["sentence_id"] for case in cases}), len(cases))
        self.assertEqual(
            Counter(case["expected_type"] for case in cases),
            counts["per_class"],
        )
        self.assertEqual(
            Counter(case["language"] for case in cases),
            counts["per_language"],
        )

    def test_sentence_ids_do_not_overlap_retired_development_sample(self):
        fresh_ids = {case["sentence_id"] for case in self.config["selected_cases"]}
        prior_ids = {case["sentence_id"] for case in self.prior["selected_cases"]}
        self.assertFalse(fresh_ids & prior_ids)

    def test_source_labels_and_constructor_provenance_are_not_conflated(self):
        source = self.config["external_source"]
        provenance = self.config["construction_provenance"]
        scope = self.config["evidence_scope"]
        self.assertEqual(source["name"], "Tatoeba")
        self.assertFalse(source["official_label_claim"])
        self.assertTrue(provenance["constructor_ai_assistance_used"])
        self.assertFalse(provenance["evaluated_qwen_model_inference_used"])
        self.assertFalse(provenance["evaluated_qwen_predictions_observed"])
        self.assertFalse(provenance["human_independent_label_validation_used"])
        self.assertFalse(scope["official_benchmark_claim_authorized"])
        self.assertFalse(scope["broad_human_likeness_claim_authorized"])

    def test_model_and_tool_carrier_are_frozen_from_v3_result(self):
        conditions = self.config["frozen_system_conditions"]
        result_lock = _load(ROOT / conditions["development_result_lock"])
        self.assertEqual(conditions["selected_model"], "qwen3.5:4b")
        self.assertEqual(
            conditions["selected_model"], result_lock["local_runtime"]["selected_model"]
        )
        self.assertEqual(
            conditions["selected_model_digest"],
            result_lock["local_runtime"]["selected_model_digest"],
        )
        self.assertEqual(
            result_lock["decision"],
            "select_qwen3_5_4b_tool_carrier_for_fresh_holdout_only",
        )

    def test_success_requires_accuracy_safety_parse_and_latency(self):
        gates = self.config["success_gates"]
        self.assertEqual(gates["candidate_correct_count_min"], 28)
        self.assertEqual(gates["candidate_none_correct"], 8)
        self.assertEqual(gates["regression_vs_rules_count_max"], 0)
        self.assertGreaterEqual(gates["newly_correct_vs_rules_count_min"], 4)
        self.assertEqual(gates["parse_success_rate_min"], 1.0)
        self.assertLessEqual(gates["fallback_call_count_max"], 20)
        self.assertLessEqual(gates["median_fallback_seconds_max"], 3.0)
        self.assertLessEqual(gates["warm_p95_fallback_seconds_max"], 5.0)

    def test_failure_cannot_be_repaired_on_the_same_holdout(self):
        self.assertFalse(
            self.config[
                "evaluated_model_inference_before_dataset_and_harness_freeze_authorized"
            ]
        )
        self.assertFalse(self.config["post_run_case_editing_authorized"])
        self.assertFalse(self.config["post_run_case_exclusion_authorized"])
        self.assertFalse(self.config["post_run_threshold_change_authorized"])
        self.assertFalse(self.config["same_holdout_prompt_tuning_authorized"])
        self.assertFalse(self.config["same_holdout_retest_authorized"])
        self.assertFalse(self.config["runtime_memory_write_authorized"])


if __name__ == "__main__":
    unittest.main()
