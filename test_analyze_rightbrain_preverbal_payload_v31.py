import unittest

from analyze_rightbrain_preverbal_payload_v31 import (
    _select_best_noncontrol,
    cluster_bootstrap_delta,
    exact_mcnemar_p,
    holm_adjust,
    paired_effect,
    summarize_condition,
)


def _case(case_id, accepted, reasons=(), tokens=100, category="daily"):
    rejected = [
        {
            "candidate_index": index,
            "raw_candidate": f"draft-{index}",
            "candidate": "",
            "rejection_reasons": list(reason_set),
        }
        for index, reason_set in enumerate(reasons)
    ]
    return {
        "id": case_id,
        "category": category,
        "generated_candidate_count": accepted + len(rejected),
        "initial_accepted_candidate_count": accepted,
        "model_initial_rejected_candidates": rejected,
        "preverbal_payload_v31": {
            "rendered_token_count": tokens,
            "rendered_character_count": tokens * 2,
            "rendered_ascii_letter_count": tokens // 2,
        },
    }


def _report(seed, cases):
    return {"seed": seed, "cases": cases}


class AnalyzeRightBrainPreverbalPayloadV31Test(unittest.TestCase):
    def test_summary_uses_seed_case_coverage_as_primary_unit(self):
        reports = [
            _report(
                1,
                [
                    _case("a", 1, [({"semantic_slots_missing:1/2"})]),
                    _case(
                        "b",
                        0,
                        [
                            ({"semantic_slots_missing:0/2", "unexpected_ascii_leak"}),
                            ({"polite_tone_drift"}),
                            (set()),
                        ],
                    ),
                ],
            )
        ]
        summary = summarize_condition(reports)
        self.assertEqual(summary["seed_case_pair_count"], 2)
        self.assertEqual(summary["strict_case_coverage_count"], 1)
        self.assertEqual(summary["strict_case_coverage_rate"], 0.5)
        self.assertEqual(summary["generated_candidate_count"], 5)
        self.assertEqual(summary["strict_accepted_candidate_count"], 1)
        self.assertEqual(summary["semantic_omission_count"], 2)
        self.assertEqual(summary["hard_surface_failure_count"], 1)
        self.assertEqual(summary["polite_tone_drift_count"], 1)

    def test_paired_effect_and_exact_mcnemar_keep_direction(self):
        summaries = {
            "treatment": {
                "strict_case_coverage_rate": 0.75,
                "pair_success": {(1, "a"): True, (1, "b"): True},
            },
            "reference": {
                "strict_case_coverage_rate": 0.25,
                "pair_success": {(1, "a"): False, (1, "b"): True},
            },
        }
        effect = paired_effect("treatment", "reference", summaries)
        self.assertEqual(effect["treatment_wins"], 1)
        self.assertEqual(effect["reference_wins"], 0)
        self.assertEqual(effect["strict_case_coverage_delta"], 0.5)
        self.assertEqual(effect["mcnemar_exact_p"], 1.0)
        self.assertEqual(exact_mcnemar_p(7, 0), 0.015625)

    def test_holm_adjustment_is_monotonic_and_covers_all_contrasts(self):
        adjusted = holm_adjust({"a": 0.01, "b": 0.02, "c": 0.5})
        self.assertEqual(set(adjusted), {"a", "b", "c"})
        self.assertAlmostEqual(adjusted["a"], 0.03)
        self.assertAlmostEqual(adjusted["b"], 0.04)
        self.assertAlmostEqual(adjusted["c"], 0.5)

    def test_cluster_bootstrap_resamples_case_not_individual_candidate(self):
        rows = [
            {
                "case_id": case_id,
                "treatment_success": treatment,
                "reference_success": reference,
            }
            for case_id, treatment, reference in [
                ("a", True, False),
                ("a", True, False),
                ("b", False, True),
                ("b", False, True),
            ]
        ]
        interval = cluster_bootstrap_delta(rows, samples=1000, seed=9)
        self.assertLessEqual(interval["lower_95"], 0)
        self.assertGreaterEqual(interval["upper_95"], 0)

    def test_best_condition_selection_follows_preregistered_lexicographic_rule(self):
        summaries = {
            "mixed_json_control": {
                "strict_case_coverage_rate": 0.2,
                "semantic_omission_rate": 0.8,
                "hard_surface_failure_rate": 0.5,
                "mean_prompt_token_count": 400,
            },
            "japanese_json": {
                "strict_case_coverage_rate": 0.4,
                "semantic_omission_rate": 0.7,
                "hard_surface_failure_rate": 0.4,
                "mean_prompt_token_count": 300,
            },
            "mixed_lines": {
                "strict_case_coverage_rate": 0.4,
                "semantic_omission_rate": 0.75,
                "hard_surface_failure_rate": 0.3,
                "mean_prompt_token_count": 200,
            },
            "japanese_lines": {
                "strict_case_coverage_rate": 0.4,
                "semantic_omission_rate": 0.7,
                "hard_surface_failure_rate": 0.45,
                "mean_prompt_token_count": 150,
            },
        }
        self.assertEqual(_select_best_noncontrol(summaries), "japanese_json")


if __name__ == "__main__":
    unittest.main()
