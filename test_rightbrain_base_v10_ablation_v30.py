import json
import unittest
from pathlib import Path

from analyze_rightbrain_base_v10_ablation_v30 import (
    classify_rejection,
    exact_mcnemar_p,
    paired_effect,
    sha256_file,
    summarize_condition,
)
from run_rightbrain_base_v10_ablation_v30 import (
    load_preregistration,
    verify_preregistered_sources,
)


ROOT = Path(__file__).resolve().parent


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


class RightBrainBaseV10FormalResultTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = ROOT / "reports/rightbrain_base_v10_ablation_v30_analysis.json"
        if not path.is_file():
            raise unittest.SkipTest("Formal V30 analysis has not been generated")
        cls.analysis = json.loads(path.read_text(encoding="utf-8"))
        if cls.analysis.get("evidence_protocol") != "amended_current_gate_rerun":
            raise unittest.SkipTest("Corrected V30 analysis has not been generated")

    def test_negative_runtime_decision_is_preserved(self):
        self.assertEqual(
            self.analysis["decision"], "keep_v10_no_runtime_change"
        )
        self.assertFalse(self.analysis["authorize_runtime_change"])
        self.assertFalse(self.analysis["authorize_human_blind_review"])

    def test_paired_result_is_exact_and_inconclusive(self):
        paired = self.analysis["paired_effect"]
        self.assertEqual(paired["pair_count"], 36)
        self.assertEqual(paired["base_only_wins"], 7)
        self.assertEqual(paired["v10_wins"], 4)
        self.assertAlmostEqual(paired["strict_case_coverage_delta"], 3 / 36)
        self.assertAlmostEqual(paired["mcnemar_exact_p"], 0.548828125)
        self.assertLess(paired["cluster_bootstrap_95"]["lower_95"], 0)
        self.assertGreater(paired["cluster_bootstrap_95"]["upper_95"], 0)

    def test_shared_failure_not_misreported_as_v10_maturity(self):
        summaries = self.analysis["condition_summary"]
        self.assertGreater(summaries["v10_adapter"]["semantic_omission_rate"], 0.75)
        self.assertGreater(summaries["base_only"]["semantic_omission_rate"], 0.75)
        self.assertTrue(self.analysis["diagnosis"]["shared_semantic_failure"])
        self.assertTrue(self.analysis["diagnosis"]["shared_hard_surface_failure"])
        self.assertEqual(
            self.analysis["diagnosis"]["adapter_effect"],
            "inconclusive_small_base_edge",
        )
        self.assertIn(
            "Base-only 在整體覆蓋率上小幅領先",
            self.analysis["diagnosis"]["interpretation_zh"],
        )
        self.assertFalse(
            self.analysis["posthoc_nonblind_surface_audit"][
                "affects_formal_score"
            ]
        )
        self.assertTrue(
            self.analysis["posthoc_nonblind_surface_audit"][
                "examples_source_verified"
            ]
        )
        self.assertEqual(
            len(self.analysis["posthoc_nonblind_surface_audit"]["examples"]),
            3,
        )

    def test_all_six_condition_reports_are_hash_bound(self):
        hashes = self.analysis["condition_report_sha256"]
        self.assertEqual(set(hashes), {"v10_adapter", "base_only"})
        self.assertTrue(all(len(rows) == 3 for rows in hashes.values()))
        for condition, rows in hashes.items():
            for seed, expected_digest in rows.items():
                report_path = (
                    ROOT
                    / "reports"
                    / f"rightbrain_base_v10_ablation_v30_{condition}_seed{seed}.json"
                )
                self.assertEqual(
                    sha256_file(report_path),
                    expected_digest,
                    f"raw report changed after analysis: {report_path.name}",
                )

    def test_preregistration_category_typo_fails_closed(self):
        self.assertEqual(self.analysis["observed_dataset_shape"]["category_count"], 9)
        self.assertEqual(
            self.analysis["observed_dataset_shape"]["preregistered_category_count"],
            8,
        )
        self.assertFalse(
            self.analysis["verification"]["preregistered_category_count_matches"]
        )
        self.assertFalse(
            self.analysis["blind_review_gates"]["all_hash_and_shape_checks_pass"]
        )


if __name__ == "__main__":
    unittest.main()
