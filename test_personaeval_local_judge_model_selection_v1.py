#!/usr/bin/env python3
"""Contract tests for the disjoint PersonaEval local-judge model pilot."""

from __future__ import annotations

import unittest

import build_personaeval_local_judge_model_selection_v1 as construction
import build_personaeval_qwen3_official_pilot_v1 as base
import run_personaeval_local_judge_model_selection_v1 as runner


class SelectionTests(unittest.TestCase):
    def test_selected_indices_are_exact(self):
        self.assertEqual(
            {
                track: construction.selected_indices(track)
                for track in construction.TRACKS
            },
            {
                "Drama": [109, 295, 340, 659, 689, 923, 1042, 1236, 1341, 1517],
                "Expertise": [21, 89, 197, 278, 344, 373, 443, 552, 612, 663],
                "Literary": [1398, 5103, 6030, 8911, 12676, 13873, 17903, 19939, 21936, 26200],
            },
        )

    def test_selection_is_disjoint_from_prior_and_smoke_rows(self):
        excluded = construction.excluded_indices()
        for track in construction.TRACKS:
            self.assertFalse(set(construction.selected_indices(track)) & excluded[track])

    def test_frozen_prompts_and_labels_are_isolated(self):
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

    def test_track_and_repeat_balance_is_exact(self):
        prereg = base.load_json(construction.PREREGISTRATION_PATH)
        prompts = base.load_json(construction.PROMPTS_PATH)["rows"]
        for track in construction.TRACKS:
            self.assertEqual(sum(row["track"] == track for row in prompts), 10)
            self.assertEqual(
                sum(row_id.startswith(track.lower()) for row_id in prereg["pilot_design"]["repeat_audit_row_ids"]),
                3,
            )
        self.assertEqual(prereg["pilot_design"]["generation_calls_per_model"], 48)
        self.assertEqual(prereg["pilot_design"]["total_generation_calls"], 96)


class PairedMetricTests(unittest.TestCase):
    @staticmethod
    def _rows(values):
        return [
            {"row_id": f"row_{index}", "correct": value}
            for index, value in enumerate(values)
        ]

    def test_paired_exact_mcnemar_is_symmetric(self):
        result = runner.paired_exact_mcnemar(
            self._rows([True, True, False, False]),
            self._rows([True, False, True, False]),
        )
        self.assertEqual(result["qwen3_4b_only_correct"], 1)
        self.assertEqual(result["qwen25_7b_only_correct"], 1)
        self.assertEqual(result["exact_two_sided_mcnemar_p_value"], 1.0)
        self.assertEqual(result["accuracy_delta_qwen25_7b_minus_qwen3_4b"], 0.0)

    def test_paired_exact_mcnemar_detects_direction(self):
        result = runner.paired_exact_mcnemar(
            self._rows([False, False, False]),
            self._rows([True, True, True]),
        )
        self.assertEqual(result["exact_two_sided_mcnemar_p_value"], 0.25)
        self.assertEqual(result["accuracy_delta_qwen25_7b_minus_qwen3_4b"], 1.0)


class DecisionTests(unittest.TestCase):
    @staticmethod
    def _measurement(*, repeat=1.0):
        return {
            "overall": {
                "parse_success_rate": 1.0,
                "exact_chance_superiority_p_value": 0.01,
                "unconditional_top1_wilson_95": [0.30, 0.70],
                "random_choice_expected_accuracy": 0.23333333333333334,
            },
            "repeat_audit": {"prediction_agreement_rate": repeat},
        }

    def setUp(self):
        self.prereg = base.load_json(construction.PREREGISTRATION_PATH)
        self.paired = {
            "exact_two_sided_mcnemar_p_value": 1.0,
            "accuracy_delta_qwen25_7b_minus_qwen3_4b": 0.0,
        }

    def test_only_passing_model_is_selected(self):
        measurements = {
            "qwen3_4b": self._measurement(repeat=0.8),
            "qwen25_7b": self._measurement(),
        }
        decision = runner._decision(self.prereg, measurements, self.paired, True)
        self.assertEqual(decision["selected_model_for_larger_validation"], "qwen25_7b")
        self.assertFalse(decision["authorize_target_person_judging"])

    def test_two_passing_models_default_to_lower_resource_model(self):
        measurements = {
            model_id: self._measurement() for model_id in construction.MODEL_ORDER
        }
        decision = runner._decision(self.prereg, measurements, self.paired, True)
        self.assertEqual(decision["selected_model_for_larger_validation"], "qwen3_4b")

    def test_neither_passing_model_is_rejected(self):
        measurements = {
            model_id: self._measurement(repeat=0.8)
            for model_id in construction.MODEL_ORDER
        }
        decision = runner._decision(self.prereg, measurements, self.paired, True)
        self.assertIsNone(decision["selected_model_for_larger_validation"])
        self.assertFalse(decision["authorize_larger_disjoint_official_evaluator_validation"])


class LockTests(unittest.TestCase):
    def test_harness_lock_is_exact(self):
        validation = runner.validate_lock()
        self.assertTrue(validation["passed"])
        self.assertTrue(all(binding["match"] for binding in validation["bindings"]))

    def test_authorization_is_narrow(self):
        prereg = base.load_json(construction.PREREGISTRATION_PATH)
        self.assertTrue(prereg["pilot_design"]["disjoint_from_previous_personaeval_pilot"])
        self.assertEqual(prereg["controlled_variables"]["batch_size"], 1)
        self.assertEqual(
            prereg["decision_rule"]["pass_authorizes_only"],
            "larger_disjoint_official_evaluator_validation",
        )
        self.assertIn("does not evaluate UruhaBrain", prereg["boundaries"][0])


if __name__ == "__main__":
    unittest.main()
