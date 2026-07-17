import json
import unittest
from collections import Counter
from pathlib import Path

from run_reflection_classifier_v1_baseline import sha256


ROOT = Path(__file__).resolve().parent
LOCK = json.loads(
    (ROOT / "configs" / "reflection_classifier_v1_baseline_result_lock.json").read_text(
        encoding="utf-8"
    )
)
RESULT_PATH = ROOT / LOCK["result_path"]
RESULT = json.loads(RESULT_PATH.read_text(encoding="utf-8"))
HARNESS_LOCK = json.loads(
    (
        ROOT / "configs" / "reflection_classifier_v1_baseline_harness_lock.json"
    ).read_text(encoding="utf-8")
)


class ReflectionClassifierV1BaselineResultTest(unittest.TestCase):
    def test_result_is_hash_locked_and_model_free(self):
        self.assertEqual(sha256(RESULT_PATH), LOCK["result_sha256"])
        self.assertEqual(RESULT["runner_commit"], LOCK["runner_commit"])
        self.assertEqual(RESULT["runner_branch"], "main")
        self.assertEqual(RESULT["model_calls"], LOCK["model_calls"])

    def test_result_uses_the_frozen_inputs_and_legacy_classifier(self):
        frozen = HARNESS_LOCK["frozen_artifacts"]
        self.assertEqual(
            RESULT["preregistration_sha256"],
            frozen["configs/reflection_classifier_v1_preregistration.json"],
        )
        self.assertEqual(
            RESULT["dataset_sha256"],
            frozen["datasets/reflection_classifier_v1_development.json"],
        )
        self.assertEqual(
            RESULT["classifier_sha256"], frozen["uruha_reflection_runtime.py"]
        )

    def test_frozen_metrics_match_raw_rows(self):
        summary = RESULT["summary"]
        for name, expected in LOCK["frozen_metrics"].items():
            self.assertEqual(summary[name], expected, name)
        self.assertEqual(summary["case_count"], LOCK["case_count"])
        self.assertEqual(len(RESULT["rows"]), LOCK["case_count"])

        false_negatives = Counter(
            row["expected_type"]
            for row in RESULT["rows"]
            if row["expected_type"] != "none" and row["observed_type"] == "none"
        )
        actual_counts = {
            label: false_negatives[label] for label in LOCK["false_negative_counts"]
        }
        self.assertEqual(actual_counts, LOCK["false_negative_counts"])

    def test_result_does_not_authorize_runtime_memory_writes(self):
        self.assertFalse(LOCK["runtime_memory_write_authorized"])
        self.assertIn("classifier_only", LOCK["decision"])


if __name__ == "__main__":
    unittest.main()
