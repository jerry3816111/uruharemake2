from __future__ import annotations

import json
import hashlib
from pathlib import Path
import unittest

from longitudinal_human_model.statistical_evaluation import (
    compare_conditions,
    exact_mcnemar_pvalue,
    exact_sign_flip_pvalue,
    probability_losses,
)
from run_m12_literature_grounded_evaluation import (
    PROTOCOL_PATH,
    ROOT,
    build_evaluation,
)


def row(sample_id, condition, actual, p_actual):
    other = "right" if actual == "left" else "left"
    return {
        "sample_id": sample_id,
        "condition": condition,
        "actual_observed_behavior": actual,
        "acceptable_behavior_labels": [actual],
        "probabilities": {actual: p_actual, other: 1 - p_actual},
    }


class StatisticalEvaluationTests(unittest.TestCase):
    def test_probability_losses_reward_more_mass_on_observed_label(self):
        strong = probability_losses(row("x", "a", "left", 0.9))
        weak = probability_losses(row("x", "b", "left", 0.4))
        self.assertLess(strong["brier"], weak["brier"])
        self.assertLess(strong["nll"], weak["nll"])
        self.assertEqual(1, strong["top1"])
        self.assertEqual(0, weak["top1"])

    def test_exact_tests_have_expected_boundaries(self):
        self.assertEqual(1.0, exact_sign_flip_pvalue([0.0, 0.0]))
        self.assertEqual(1.0, exact_mcnemar_pvalue(0, 0))
        self.assertLess(exact_mcnemar_pvalue(8, 0), 0.01)

    def test_paired_comparison_uses_same_sample_ids(self):
        rows = [
            row("x1", "candidate", "left", 0.9),
            row("x2", "candidate", "right", 0.8),
            row("x1", "baseline", "left", 0.6),
            row("x2", "baseline", "right", 0.55),
        ]
        result = compare_conditions(
            rows,
            candidate_condition="candidate",
            baseline_condition="baseline",
            bootstrap_repetitions=200,
        )
        self.assertEqual(2, result["sample_count"])
        self.assertLess(result["brier"]["mean_delta"], 0)
        self.assertLess(result["nll"]["mean_delta"], 0)
        self.assertEqual("directionally_favors_candidate", result["directional_verdict"])

    def test_rejects_unpaired_rows(self):
        rows = [
            row("x1", "candidate", "left", 0.9),
            row("x2", "baseline", "left", 0.6),
        ]
        with self.assertRaisesRegex(ValueError, "sample IDs"):
            compare_conditions(
                rows,
                candidate_condition="candidate",
                baseline_condition="baseline",
                bootstrap_repetitions=10,
            )

    def test_protocol_hashes_and_current_evidence_boundary(self):
        protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
        self.assertEqual("posthoc_protocol_on_frozen_results_not_preregistration", protocol["status"])
        for binding in protocol["tracks"] + list(protocol["auxiliary_artifacts"].values()):
            self.assertTrue((ROOT / binding["path"]).is_file())
        result = build_evaluation(bootstrap_repetitions=200)
        self.assertEqual(3, result["replication"]["track_count"])
        self.assertFalse(result["replication"]["central_same_model_superiority_supported"])
        self.assertEqual(0, result["replication"]["formal_real_person_track_count"])
        self.assertEqual(
            "bounded_persistence_over_recent_but_no_task_advantage_over_full_context",
            result["long_memory"]["verdict"],
        )
        self.assertFalse(result["faithfulness"]["stable_component_importance_supported"])

    def test_frozen_result_lock_matches_all_artifacts(self):
        lock_path = ROOT / "configs/m12_literature_grounded_evaluation_result_lock.json"
        lock = json.loads(lock_path.read_text(encoding="utf-8"))
        self.assertFalse(lock["central_same_model_superiority_supported"])
        self.assertEqual(0, lock["formal_real_person_track_count"])
        for artifact in lock["artifacts"].values():
            actual = hashlib.sha256((ROOT / artifact["path"]).read_bytes()).hexdigest()
            self.assertEqual(artifact["sha256"], actual, artifact["path"])


if __name__ == "__main__":
    unittest.main()
