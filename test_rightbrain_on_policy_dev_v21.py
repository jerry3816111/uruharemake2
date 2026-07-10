import unittest

from build_rightbrain_on_policy_preference_v21 import _failure_family, build_pairs
from eval_rightbrain_model_surface_holdout import build_report
from rightbrain_on_policy_dev_cases_v21 import case_inputs, validate_cases


def _strict_chosen(case):
    parts = []
    anchor = str(case.get("expected_anchor") or "")
    if anchor:
        parts.append(anchor)
    for group in case["required_marker_groups"]:
        marker = str(group[0])
        if marker not in "。".join(parts):
            parts.append(marker)
    return "。".join(parts) + "。"


def _raw_report(seed, rejection_index):
    reasons = [
        "semantic_slots_missing:0/2",
        "unexpected_ascii_leak",
        "polite_tone_drift",
        "cjk_language_leak",
    ]
    rows = []
    for index, case in enumerate(case_inputs()):
        rows.append(
            {
                "id": case["id"],
                "model_accepted_candidates": [
                    {
                        "source": "initial",
                        "candidate": _strict_chosen(case),
                        "score": 8.0,
                    }
                ],
                "model_initial_rejected_candidates": [
                    {
                        "raw_candidate": (
                            "分からない。" if rejection_index == 0 else "今は無理だ。"
                        ),
                        "rejection_reasons": [reasons[(index + rejection_index) % len(reasons)]],
                    }
                ],
            }
        )
    return {
        "adapter_ref": "uruha_rightbrain_plan_sft_lora_v10_expanded_rejection_v1",
        "load_model": True,
        "seed": seed,
        "summary": {"generated_candidate_count": 48},
        "cases": rows,
    }


class RightBrainOnPolicyDevV21Test(unittest.TestCase):
    def test_failure_family_collapses_duplicate_runtime_and_strict_labels(self):
        self.assertEqual(
            _failure_family("strict_semantic_slots_missing:1/2"),
            "semantic_slots_missing",
        )
        self.assertEqual(_failure_family("unexpected_ascii_leak"), "ascii_leak")
        self.assertEqual(_failure_family("cjk_language_leak"), "language_pollution")

    def test_cases_are_source_separated_from_promotion_holdout(self):
        validation = validate_cases()

        self.assertTrue(validation["valid"])
        self.assertEqual(validation["case_count"], 16)
        self.assertEqual(validation["source_family_count"], 8)
        self.assertEqual(validation["promotion_holdout_case_overlap_count"], 0)
        self.assertEqual(validation["promotion_holdout_input_overlap_count"], 0)

    def test_surface_runner_accepts_external_case_set_without_changing_default_api(self):
        report = build_report(
            load_model=False,
            cases=case_inputs()[:1],
            scope="custom_v21_test",
            conclusion_zh="custom",
        )

        self.assertEqual(report["scope"], "custom_v21_test")
        self.assertEqual(report["summary"]["case_count"], 1)
        self.assertEqual(report["cases"][0]["source_family"], "reply_uncertainty")

    def test_builder_uses_only_same_policy_strict_chosen_and_rejected(self):
        rows, summary = build_pairs(
            [_raw_report(1, 0), _raw_report(2, 1)],
            promotion_holdout_outputs=set(),
        )

        self.assertEqual(len(rows), 32)
        self.assertTrue(summary["authorize_preference_probe"])
        self.assertEqual(summary["source_family_count"], 8)
        self.assertEqual(summary["strict_chosen_case_count"], 16)
        self.assertTrue(
            all(row["chosen_origin"] == "v10_strict_quality_accepted" for row in rows)
        )
        self.assertTrue(all(row["rejected_origin"].startswith("v10_") for row in rows))

    def test_builder_blocks_report_without_real_model_evidence(self):
        first = _raw_report(1, 0)
        second = _raw_report(2, 1)
        second["load_model"] = False

        _, summary = build_pairs(
            [first, second],
            promotion_holdout_outputs=set(),
        )

        self.assertFalse(summary["authorize_preference_probe"])
        self.assertFalse(summary["gates"]["every_source_report_loaded_real_model"])


if __name__ == "__main__":
    unittest.main()
