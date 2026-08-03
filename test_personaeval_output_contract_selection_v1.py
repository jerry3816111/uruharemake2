#!/usr/bin/env python3
"""Contract tests for the PersonaEval output-contract selection pilot."""

from __future__ import annotations

import unittest

import build_personaeval_output_contract_selection_v1 as construction
import build_personaeval_qwen3_official_pilot_v1 as base
import run_personaeval_output_contract_selection_v1 as runner


class SelectionTests(unittest.TestCase):
    def test_selected_indices_are_exact(self):
        self.assertEqual(
            {track: construction.selected_indices(track) for track in construction.TRACKS},
            {
                "Drama": [41, 270, 497, 614, 787, 890, 1007, 1162, 1381, 1506],
                "Expertise": [39, 111, 168, 219, 288, 414, 459, 523, 572, 631],
                "Literary": [1919, 3416, 6064, 9699, 12034, 15087, 16244, 19754, 21581, 26181],
            },
        )

    def test_selection_is_disjoint_from_all_previous_rows(self):
        excluded = construction.excluded_indices()
        for track in construction.TRACKS:
            self.assertFalse(set(construction.selected_indices(track)) & excluded[track])

    def test_prompt_and_label_files_are_isolated(self):
        prompts = base.load_json(construction.PROMPTS_PATH)
        labels = base.load_json(construction.LABELS_PATH)
        self.assertEqual(len(prompts["rows"]), 30)
        self.assertEqual(
            [row["row_id"] for row in prompts["rows"]],
            [row["row_id"] for row in labels["rows"]],
        )
        for row in prompts["rows"]:
            self.assertNotIn("gt", row)
            self.assertNotIn("ground_truth", row)
            self.assertNotIn("label_sha256", row)

    def test_track_repeat_and_generation_counts_are_exact(self):
        prereg = base.load_json(construction.PREREGISTRATION_PATH)
        prompts = base.load_json(construction.PROMPTS_PATH)["rows"]
        for track in construction.TRACKS:
            self.assertEqual(sum(row["track"] == track for row in prompts), 10)
            self.assertEqual(
                sum(
                    row_id.startswith(track.lower())
                    for row_id in prereg["pilot_design"]["repeat_audit_row_ids"]
                ),
                3,
            )
        self.assertEqual(prereg["pilot_design"]["generation_calls_per_condition"], 48)
        self.assertEqual(prereg["pilot_design"]["total_generation_calls"], 96)


class ParserTests(unittest.TestCase):
    def test_candidate_parser_accepts_only_exact_option(self):
        options = ["Alpha", "Beta", "Gamma", "Delta"]
        self.assertEqual(runner.parse_candidate_name("Beta", options), "Beta")
        for invalid in (" Beta", "Beta\n", '"Beta"', '{"choice":"Beta"}', "beta"):
            with self.assertRaises(ValueError):
                runner.parse_candidate_name(invalid, options)


class MetricTests(unittest.TestCase):
    @staticmethod
    def _paired_rows(strict_values, candidate_values):
        strict = [
            {"row_id": f"row_{index}", "correct": value}
            for index, value in enumerate(strict_values)
        ]
        candidate = [
            {"row_id": f"row_{index}", "correct": value}
            for index, value in enumerate(candidate_values)
        ]
        return strict, candidate

    def test_mcnemar_is_paired_and_directional(self):
        strict, candidate = self._paired_rows(
            [False, False, False], [True, True, True]
        )
        result = runner.paired_exact_mcnemar(strict, candidate)
        self.assertEqual(result["strict_only_correct"], 0)
        self.assertEqual(result["candidate_only_correct"], 3)
        self.assertEqual(result["exact_two_sided_mcnemar_p_value"], 0.25)
        self.assertEqual(result["accuracy_delta_candidate_minus_strict"], 1.0)


class DecisionTests(unittest.TestCase):
    @staticmethod
    def _condition(*, parse, accuracy, chance_p, lower, repeat):
        return {
            "overall": {
                "parse_success_rate": parse,
                "unconditional_top1_accuracy": accuracy,
                "exact_chance_superiority_p_value": chance_p,
                "unconditional_top1_wilson_95": [lower, 0.8],
                "random_choice_expected_accuracy": 0.23333333333333334,
            },
            "repeat_audit": {"prediction_agreement_rate": repeat},
        }

    def setUp(self):
        self.prereg = base.load_json(construction.PREREGISTRATION_PATH)
        self.paired = {"accuracy_delta_candidate_minus_strict": 0.1}

    def test_candidate_contract_pass_requires_every_gate(self):
        measurements = {
            "strict_probability": self._condition(
                parse=0.90, accuracy=0.40, chance_p=0.1, lower=0.2, repeat=0.9
            ),
            "candidate_name": self._condition(
                parse=1.0, accuracy=0.50, chance_p=0.01, lower=0.30, repeat=1.0
            ),
        }
        decision = runner._decision(self.prereg, measurements, self.paired, True)
        self.assertTrue(decision["passed"])
        self.assertEqual(
            decision["selected_contract_for_larger_validation"], "candidate_name"
        )
        self.assertFalse(decision["authorize_target_person_judging"])

    def test_accuracy_regression_rejects_candidate_contract(self):
        measurements = {
            "strict_probability": self._condition(
                parse=0.90, accuracy=0.60, chance_p=0.01, lower=0.3, repeat=1.0
            ),
            "candidate_name": self._condition(
                parse=1.0, accuracy=0.50, chance_p=0.01, lower=0.30, repeat=1.0
            ),
        }
        decision = runner._decision(self.prereg, measurements, self.paired, True)
        self.assertFalse(decision["passed"])
        self.assertFalse(decision["checks"]["accuracy_noninferiority_point_gate"])


class LockTests(unittest.TestCase):
    def test_harness_lock_is_exact(self):
        validation = runner.validate_lock()
        self.assertTrue(validation["passed"])
        self.assertTrue(all(binding["match"] for binding in validation["bindings"]))

    def test_authorization_is_narrow_and_adapted(self):
        prereg = base.load_json(construction.PREREGISTRATION_PATH)
        self.assertTrue(prereg["compatibility_boundary"]["candidate_name_condition_is_adapted_transport"])
        self.assertFalse(prereg["compatibility_boundary"]["direct_official_leaderboard_comparability"])
        self.assertEqual(
            prereg["decision_rule"]["pass_authorizes_only"],
            "larger_disjoint_adapted_evaluator_validation",
        )


if __name__ == "__main__":
    unittest.main()
