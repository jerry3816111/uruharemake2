#!/usr/bin/env python3
"""Contract tests for the official PersonaEval local evaluator pilot."""

from __future__ import annotations

import json
import unittest

import build_personaeval_qwen3_official_pilot_v1 as construction
import run_personaeval_qwen3_official_pilot_v1 as runner


EXPECTED_INDICES = {
    "Drama": [
        34, 111, 203, 286, 391, 433, 503, 647, 680, 755,
        886, 913, 1023, 1143, 1201, 1277, 1339, 1483, 1557, 1594,
    ],
    "Expertise": [
        7, 42, 100, 117, 165, 177, 242, 250, 295, 340,
        380, 416, 440, 478, 509, 551, 589, 627, 633, 679,
    ],
    "Literary": [
        329, 1868, 3620, 5093, 6036, 6685, 8811, 9229, 10888, 12411,
        14305, 15150, 16638, 18161, 18492, 19752, 21578, 22335, 23762, 26092,
    ],
}


class SelectionContractTests(unittest.TestCase):
    def test_selected_indices_are_exact_and_label_blind(self):
        for track, contract in construction.TRACKS.items():
            self.assertEqual(
                construction.selected_indices(track, contract["row_count"]),
                EXPECTED_INDICES[track],
            )

    def test_frozen_prompt_and_label_files_are_isolated(self):
        prompts = construction.load_json(construction.PROMPTS_PATH)
        labels = construction.load_json(construction.LABELS_PATH)
        self.assertEqual(len(prompts["rows"]), 60)
        self.assertEqual(len(labels["rows"]), 60)
        self.assertEqual(
            [row["row_id"] for row in prompts["rows"]],
            [row["row_id"] for row in labels["rows"]],
        )
        for row in prompts["rows"]:
            self.assertNotIn("gt", row)
            self.assertNotIn("ground_truth", row)
            self.assertNotIn("label_sha256", row)
            self.assertEqual(len(row["options"]), row["option_count"])

    def test_track_and_repeat_balance_is_exact(self):
        prompts = construction.load_json(construction.PROMPTS_PATH)
        rows = prompts["rows"]
        for track in construction.TRACKS:
            self.assertEqual(sum(row["track"] == track for row in rows), 20)
        audit_ids = construction.repeat_audit_row_ids(rows)
        self.assertEqual(len(audit_ids), 12)
        by_id = {row["row_id"]: row for row in rows}
        for track in construction.TRACKS:
            self.assertEqual(sum(by_id[row_id]["track"] == track for row_id in audit_ids), 4)


class OfficialParserCompatibilityTests(unittest.TestCase):
    def test_four_option_code_block(self):
        options = ["A", "B", "C", "D"]
        response = "analysis\n```json\n{\"A\":0.1,\"B\":0.2,\"C\":0.6,\"D\":0.1}\n```"
        parsed = runner.parse_official_probability_response(response, options)
        self.assertEqual(runner._prediction(parsed), "C")

    def test_five_option_expertise_is_supported(self):
        options = ["Child", "Teen", "College", "Graduate", "Expert"]
        response = json.dumps(
            {"Child": 0.05, "Teen": 0.05, "College": 0.1, "Graduate": 0.2, "Expert": 0.6}
        )
        parsed = runner.parse_official_probability_response(response, options)
        self.assertEqual(len(parsed), 5)
        self.assertEqual(runner._prediction(parsed), "Expert")

    def test_json_repair_matches_official_dependency_behavior(self):
        options = ["A", "B", "C", "D"]
        parsed = runner.parse_official_probability_response(
            "{'A': 0.1, 'B': 0.2, 'C': 0.3, 'D': 0.4}", options
        )
        self.assertEqual(parsed["D"], 0.4)

    def test_invalid_distribution_is_rejected(self):
        options = ["A", "B", "C", "D"]
        with self.assertRaises(ValueError):
            runner.parse_official_probability_response(
                '{"A":0.4,"B":0.4,"C":0.4,"D":-0.2}', options
            )
        with self.assertRaises(ValueError):
            runner.parse_official_probability_response(
                '{"A":0.4,"B":0.4,"C":0.1,"D":0.0}', options
            )


class MetricTests(unittest.TestCase):
    def _row(self, *, parsed, correct, option_count=4, rank=1):
        options = [f"O{i}" for i in range(option_count)]
        probabilities = None
        if parsed:
            probabilities = {option: 0.0 for option in options}
            probabilities[options[0]] = 1.0
        return {
            "parse_success": parsed,
            "correct": correct,
            "ground_truth_rank": rank if parsed else None,
            "ground_truth": options[0] if correct else options[-1],
            "options": options,
            "option_count": option_count,
            "probabilities": probabilities,
            "prompt_tokens": 10,
            "completion_tokens": 2,
            "generation_seconds": 0.1,
        }

    def test_parse_errors_count_as_wrong_in_primary_accuracy(self):
        rows = [
            self._row(parsed=True, correct=True),
            self._row(parsed=True, correct=False),
            self._row(parsed=False, correct=False),
        ]
        metrics = runner._metrics(rows)
        self.assertEqual(metrics["parsed_count"], 2)
        self.assertAlmostEqual(metrics["unconditional_top1_accuracy"], 1 / 3)
        self.assertAlmostEqual(metrics["conditional_top1_accuracy"], 1 / 2)

    def test_mixed_four_and_five_option_random_baseline(self):
        rows = []
        for _ in range(20):
            rows.append(self._row(parsed=True, correct=False, option_count=4, rank=2))
        for _ in range(20):
            rows.append(self._row(parsed=True, correct=False, option_count=5, rank=2))
        for _ in range(20):
            rows.append(self._row(parsed=True, correct=False, option_count=4, rank=2))
        metrics = runner._metrics(rows)
        self.assertAlmostEqual(metrics["random_choice_expected_accuracy"], 7 / 30)
        self.assertAlmostEqual(
            runner._poisson_binomial_tail(
                [0.25] * 20 + [0.2] * 20 + [0.25] * 20, 21
            ),
            0.027149679753641326,
        )


class PreregistrationTests(unittest.TestCase):
    def test_preregistration_has_narrow_authorization(self):
        prereg = construction.load_json(construction.PREREGISTRATION_PATH)
        self.assertEqual(prereg["pilot_design"]["primary_row_count"], 60)
        self.assertEqual(prereg["pilot_design"]["generation_call_count"], 84)
        self.assertEqual(
            prereg["decision_gate"]["pilot_pass_authorizes_only"],
            "preregister_larger_official_personaeval_validation",
        )
        self.assertTrue(all(prereg["prohibited_actions"].values()))
        self.assertTrue(prereg["label_isolation"]["label_file_loaded_after_all_generation_calls"])
        self.assertEqual(
            prereg["official_harness_compatibility"]["prediction_rule"],
            "argmax_over_returned_candidate_probabilities",
        )
        self.assertEqual(
            prereg["controlled_variables"]["system_message"],
            construction.SYSTEM_MESSAGE,
        )
        self.assertFalse(
            prereg["official_harness_compatibility"]["direct_official_leaderboard_comparability"]
        )

    def test_harness_lock_is_exact(self):
        validation = runner.validate_lock()
        self.assertTrue(validation["passed"])
        self.assertTrue(all(binding["match"] for binding in validation["bindings"]))


if __name__ == "__main__":
    unittest.main()
