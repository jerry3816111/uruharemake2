import hashlib
import json
import unittest
from pathlib import Path

import uruha_reflection_runtime as reflection


ROOT = Path(__file__).resolve().parent
AMENDMENT_PATH = (
    ROOT
    / "configs"
    / "reflection_hybrid_classifier_v4_independent_holdout_protocol_amendment.json"
)


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ReflectionHybridClassifierV4IndependentHoldoutProtocolAmendmentTest(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls):
        cls.amendment = _load(AMENDMENT_PATH)
        bindings = cls.amendment["artifact_bindings"]
        cls.preregistration = _load(ROOT / bindings["original_preregistration"])
        cls.dataset = _load(ROOT / bindings["holdout_dataset"])

    def test_every_feasibility_input_is_hash_bound(self):
        bindings = self.amendment["artifact_bindings"]
        for key, expected in bindings.items():
            if not key.endswith("_sha256"):
                continue
            path_key = key.removesuffix("_sha256")
            self.assertIn(path_key, bindings)
            self.assertEqual(_sha256(ROOT / bindings[path_key]), expected, path_key)

    def test_rules_none_snapshot_recomputes_exactly(self):
        observed = [
            case["id"]
            for case in self.dataset["cases"]
            if reflection.classify_reflection_type(case["text"]) == "none"
        ]
        snapshot = self.amendment["frozen_rules_feasibility_snapshot"]
        self.assertEqual(observed, snapshot["rules_none_case_ids"])
        self.assertEqual(len(observed), snapshot["rules_none_count"])
        self.assertEqual(len(observed), 22)

    def test_original_resource_ceiling_is_impossible_for_full_coverage(self):
        original = self.preregistration["success_gates"]["fallback_call_count_max"]
        required = self.amendment["frozen_rules_feasibility_snapshot"][
            "rules_none_count"
        ]
        self.assertEqual(original, 20)
        self.assertGreater(required, original)

    def test_correction_changes_only_the_non_predictive_call_ceiling(self):
        change = self.amendment["protocol_change"]
        self.assertEqual(change["field"], "success_gates.fallback_call_count_max")
        self.assertEqual(change["original_value"], 20)
        self.assertEqual(change["corrected_value"], 22)
        for key, value in change.items():
            if key.startswith("changes_"):
                self.assertFalse(value, key)
        original = dict(self.preregistration["success_gates"])
        original.pop("fallback_call_count_max")
        self.assertEqual(original, self.amendment["unchanged_success_gates"])

    def test_no_qwen_result_or_runtime_use_is_authorized(self):
        trigger = self.amendment["trigger"]
        self.assertEqual(trigger["evaluated_qwen_model_calls_before_finding"], 0)
        self.assertFalse(trigger["evaluated_qwen_predictions_observed"])
        self.assertFalse(
            self.amendment[
                "evaluated_qwen_inference_before_amendment_merge_authorized"
            ]
        )
        self.assertFalse(self.amendment["same_holdout_prompt_tuning_authorized"])
        self.assertFalse(self.amendment["same_holdout_case_editing_authorized"])
        self.assertFalse(self.amendment["same_holdout_label_editing_authorized"])
        self.assertFalse(self.amendment["runtime_memory_write_authorized"])


if __name__ == "__main__":
    unittest.main()
