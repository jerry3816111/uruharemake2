import unittest

from compare_rightbrain_model_surface_holdouts import build_comparison


def _report(adapter, accepted, reasons=None):
    reasons = reasons or []
    return {
        "scope": "rightbrain_model_blend_surface_holdout_eval",
        "adapter_ref": adapter,
        "load_model": True,
        "seed": 20260624,
        "candidate_count_per_case": 1,
        "runtime_contract_version": "plan_surface_contract_v1",
        "summary": {
            "generated_candidate_count": 10,
            "accepted_candidate_count": accepted,
            "raw_candidate_acceptance_rate": accepted / 10,
            "model_selected_case_count": 1,
            "model_selected_case_rate": 1 / 11,
            "final_quality_pass_rate": 1.0,
            "final_language_clean_rate": 1.0,
            "final_forbidden_surface_leak_rate": 0.0,
            "final_generic_template_hit_rate": 0.0,
            "final_normalized_duplicate_reply_rate": 0.0,
        },
        "cases": [
            {
                "id": "support_case",
                "category": "support",
                "accepted_candidate_count": int(accepted > 4),
                "model_rejection_reasons": reasons,
                "selected_source": "deterministic",
            }
        ],
    }


class CompareRightBrainModelSurfaceHoldoutsTest(unittest.TestCase):
    def setUp(self):
        self.training = {
            "rows": 1061,
            "supplemental_rows": 36,
            "optimizer_updates": 15,
            "nonfinite_skips": 0,
            "initial_eval_loss_probe": 3.06,
            "sampled_eval_loss": 3.05,
            "final_train_loss": 3.21,
            "learning_rate": 3e-7,
        }

    def test_builds_matched_delta_and_newly_accepted_case(self):
        baseline = _report(
            "v9",
            4,
            ["polite_tone_drift", "semantic_slots_missing:2/3"],
        )
        trained = _report("v10", 5)

        report = build_comparison(baseline, trained, self.training)

        acceptance = next(
            row
            for row in report["metric_rows"]
            if row["metric"] == "raw_candidate_acceptance_rate"
        )
        self.assertEqual(acceptance["delta"], 0.1)
        self.assertEqual(report["case_diffs"][0]["id"], "support_case")
        self.assertTrue(report["case_diffs"][0]["newly_accepted"])
        self.assertEqual(
            report["case_diffs"][0]["resolved_rejection_reasons"],
            ["polite_tone_drift", "semantic_slots_missing:2/3"],
        )

    def test_rejects_unmatched_seed(self):
        baseline = _report("v9", 4)
        trained = _report("v10", 5)
        trained["seed"] = 99

        with self.assertRaisesRegex(ValueError, "seed"):
            build_comparison(baseline, trained, self.training)

    def test_rejects_non_model_baseline(self):
        baseline = _report("v9", 4)
        trained = _report("v10", 5)
        baseline["load_model"] = False

        with self.assertRaisesRegex(ValueError, "model-loaded"):
            build_comparison(baseline, trained, self.training)


if __name__ == "__main__":
    unittest.main()
