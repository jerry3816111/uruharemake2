import json
import unittest
from pathlib import Path

import uruha_reflection_runtime as reflection
from run_reflection_classifier_v1_baseline import sha256


ROOT = Path(__file__).resolve().parent
LOCK = json.loads(
    (ROOT / "configs" / "reflection_classifier_v1_candidate_result_lock.json").read_text(
        encoding="utf-8"
    )
)
RESULT_PATH = ROOT / LOCK["result_path"]
RESULT = json.loads(RESULT_PATH.read_text(encoding="utf-8"))
BASELINE = json.loads(
    (ROOT / "reports" / "reflection_classifier_v1_legacy_baseline.json").read_text(
        encoding="utf-8"
    )
)
HARNESS_LOCK = json.loads(
    (
        ROOT / "configs" / "reflection_classifier_v1_candidate_harness_lock.json"
    ).read_text(encoding="utf-8")
)


class ReflectionClassifierV1CandidateResultTest(unittest.TestCase):
    def test_result_is_hash_locked_and_model_free(self):
        self.assertEqual(sha256(RESULT_PATH), LOCK["result_sha256"])
        self.assertEqual(RESULT["runner_commit"], LOCK["runner_commit"])
        self.assertEqual(RESULT["runner_branch"], "main")
        self.assertEqual(RESULT["model_calls"], LOCK["model_calls"])

    def test_result_uses_frozen_candidate_and_inputs(self):
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
            RESULT["baseline_sha256"],
            frozen["reports/reflection_classifier_v1_legacy_baseline.json"],
        )
        self.assertEqual(
            RESULT["candidate_classifier_sha256"],
            frozen["uruha_reflection_runtime.py"],
        )

    def test_pairwise_delta_matches_raw_rows(self):
        baseline_by_id = {row["id"]: row for row in BASELINE["rows"]}
        candidate_by_id = {row["id"]: row for row in RESULT["rows"]}
        self.assertEqual(set(baseline_by_id), set(candidate_by_id))

        newly_correct = [
            case_id
            for case_id, row in candidate_by_id.items()
            if row["correct"] and not baseline_by_id[case_id]["correct"]
        ]
        regressions = [
            case_id
            for case_id, row in candidate_by_id.items()
            if not row["correct"] and baseline_by_id[case_id]["correct"]
        ]
        self.assertEqual(len(newly_correct), LOCK["newly_correct_count"])
        self.assertEqual(len(regressions), LOCK["regression_count"])
        self.assertEqual(BASELINE["summary"]["overall_accuracy"], LOCK["baseline_accuracy"])
        self.assertEqual(RESULT["summary"]["overall_accuracy"], LOCK["candidate_accuracy"])
        self.assertAlmostEqual(
            LOCK["candidate_accuracy"] - LOCK["baseline_accuracy"],
            LOCK["absolute_accuracy_delta"],
            places=4,
        )
        self.assertTrue(RESULT["summary"]["all_gates_pass"])

    def test_result_authorizes_holdout_but_not_runtime(self):
        self.assertIn("holdout_only", LOCK["decision"])
        self.assertFalse(LOCK["runtime_memory_write_authorized"])
        self.assertFalse(LOCK["downstream_behavior_claim_authorized"])
        self.assertFalse(reflection.typed_reflection_runtime_enabled({}))


if __name__ == "__main__":
    unittest.main()
