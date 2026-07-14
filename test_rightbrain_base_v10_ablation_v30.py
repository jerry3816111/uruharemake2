import unittest

from analyze_rightbrain_base_v10_ablation_v30 import (
    classify_rejection,
    exact_mcnemar_p,
    paired_effect,
    summarize_condition,
)
from run_rightbrain_base_v10_ablation_v30 import (
    load_preregistration,
    verify_preregistered_sources,
)


def _case(case_id, accepted, reasons=(), category="support"):
    rejected = []
    for index, reason_set in enumerate(reasons):
        rejected.append(
            {
                "candidate_index": index,
                "raw_candidate": "draft",
                "candidate": "",
                "rejection_reasons": list(reason_set),
            }
        )
    return {
        "id": case_id,
        "category": category,
        "generated_candidate_count": accepted + len(rejected),
        "initial_accepted_candidate_count": accepted,
        "model_initial_rejected_candidates": rejected,
    }


def _report(seed, cases):
    return {"seed": seed, "cases": cases}


class RightBrainBaseV10AblationV30Test(unittest.TestCase):
    def test_preregistered_sources_are_still_frozen(self):
        checks = verify_preregistered_sources(load_preregistration())
        self.assertTrue(checks)
        self.assertTrue(all(checks.values()))

    def test_rejection_dimensions_are_separate(self):
        flags = classify_rejection(
            [
                "unexpected_ascii_leak",
                "semantic_slots_missing:1/3",
                "polite_tone_drift",
            ]
        )
        self.assertEqual(
            flags,
            {
                "hard_surface_failure": True,
                "semantic_omission": True,
                "polite_tone_drift": True,
                "duplicate_candidate": False,
            },
        )

    def test_summary_uses_seed_case_coverage_as_primary_unit(self):
        summary = summarize_condition(
            [
                _report(
                    1,
                    [
                        _case("a", 1, [("semantic_slots_missing:1/2",)]),
                        _case("b", 0, [("unexpected_ascii_leak",)] * 3),
                    ],
                )
            ]
        )
        self.assertEqual(summary["seed_case_pair_count"], 2)
        self.assertEqual(summary["strict_case_coverage_count"], 1)
        self.assertEqual(summary["strict_case_coverage_rate"], 0.5)
        self.assertEqual(summary["generated_candidate_count"], 5)
        self.assertEqual(summary["strict_accepted_candidate_count"], 1)

    def test_paired_effect_and_exact_mcnemar(self):
        v10 = summarize_condition(
            [_report(1, [_case("a", 1), _case("b", 0, [()] * 3)])]
        )
        base = summarize_condition(
            [_report(1, [_case("a", 1), _case("b", 1, [()] * 2)])]
        )
        effect = paired_effect(v10, base)
        self.assertEqual(effect["base_only_wins"], 1)
        self.assertEqual(effect["v10_wins"], 0)
        self.assertEqual(effect["strict_case_coverage_delta"], 0.5)
        self.assertEqual(effect["mcnemar_exact_p"], 1.0)
        self.assertEqual(exact_mcnemar_p(6, 0), 0.03125)


if __name__ == "__main__":
    unittest.main()
