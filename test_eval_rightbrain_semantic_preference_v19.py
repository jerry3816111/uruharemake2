import copy
import unittest

from eval_rightbrain_semantic_preference_v19 import build_report


def _preference(rate, margin, target_rate=0.5):
    return {
        "chosen_preference_rate": rate,
        "mean_raw_preference_margin": margin,
        "target_margin_rate": target_rate,
    }


def _training_report():
    return {
        "output_adapter_ref": "v19",
        "source_overlap_count": 0,
        "target_pair_steps": 24,
        "grad_accum": 4,
        "optimizer_updates": 6,
        "nonfinite_skips": 0,
        "max_observed_gradient_norm": 2.0,
        "initial_eval_preference": _preference(0.5, -0.05, 0.0),
        "final_train_preference": _preference(0.8, 0.1, 0.7),
        "final_eval_preference": _preference(0.75, 0.02, 0.5),
    }


class RightBrainSemanticPreferenceV19DecisionTest(unittest.TestCase):
    def test_authorizes_stable_unseen_improvement(self):
        report = build_report(_training_report())

        self.assertTrue(report["authorize_actual_model_holdout"])
        self.assertTrue(all(report["gates"].values()))

    def test_blocks_nonfinite_or_non_generalizing_run(self):
        training = copy.deepcopy(_training_report())
        training["nonfinite_skips"] = 1
        training["final_eval_preference"] = _preference(0.5, -0.06, 0.0)

        report = build_report(training)

        self.assertFalse(report["authorize_actual_model_holdout"])
        self.assertFalse(report["gates"]["nonfinite_training_events_are_zero"])


if __name__ == "__main__":
    unittest.main()
