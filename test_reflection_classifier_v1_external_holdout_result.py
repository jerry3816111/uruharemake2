import hashlib
import json
import unittest
from pathlib import Path

import uruha_reflection_runtime as reflection
from reflection_classifier_v1_external_holdout_core import analyze_matched


ROOT = Path(__file__).resolve().parent
RESULT_LOCK_PATH = (
    ROOT / "configs" / "reflection_classifier_v1_external_holdout_result_lock.json"
)


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ReflectionClassifierV1ExternalHoldoutResultTest(unittest.TestCase):
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

    def test_analysis_recomputes_exactly_from_frozen_raw_rows(self):
        recomputed = analyze_matched(
            self.dataset["cases"],
            self.raw["rows"],
            self.preregistration["success_gates"],
        )
        self.assertEqual(recomputed, self.analysis["matched_result"])

    def test_formal_run_provenance_and_model_accounting_are_exact(self):
        self.assertEqual(self.raw["runner_branch"], "main")
        self.assertEqual(self.raw["runner_commit"], self.lock["runner_commit"])
        self.assertEqual(self.raw["case_count"], 32)
        self.assertEqual(self.raw["model_calls"], 0)
        self.assertFalse(self.raw["gold_label_passed_to_classifier"])

    def test_candidate_did_not_generalize_beyond_legacy_on_this_holdout(self):
        result = self.analysis["matched_result"]
        self.assertEqual(result["legacy"]["correct_count"], 20)
        self.assertEqual(result["candidate"]["correct_count"], 20)
        self.assertEqual(result["legacy"]["accuracy"], 0.625)
        self.assertEqual(result["candidate"]["accuracy"], 0.625)
        self.assertEqual(result["accuracy_delta"], 0.0)
        self.assertEqual(result["newly_correct_count"], 0)
        self.assertEqual(result["regression_count"], 0)
        self.assertTrue(
            all(
                row["legacy_observed_type"] == row["candidate_observed_type"]
                for row in result["rows"]
            )
        )

    def test_failed_gates_reject_runtime_advancement(self):
        result = self.analysis["matched_result"]
        self.assertFalse(result["all_gates_pass"])
        self.assertEqual(sum(result["gate_checks"].values()), 3)
        self.assertIn("reject_runtime_advancement", self.analysis["decision"])
        self.assertFalse(self.analysis["runtime_memory_write_authorized"])
        self.assertFalse(self.lock["same_holdout_retest_authorized"])
        self.assertFalse(reflection.typed_reflection_runtime_enabled({}))


if __name__ == "__main__":
    unittest.main()
