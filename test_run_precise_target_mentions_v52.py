#!/usr/bin/env python3

import json
import unittest

from precise_target_mentions_v52 import audit_precise_event_maps
from run_precise_target_mentions_v52 import (
    CONFIG_PATH,
    DATASET_PATH,
    V44_LOCK_PATH,
    V45_CONFIG_PATH,
    V51_CONFIG_PATH,
    _validate_inputs,
    build_candidate_rows,
    build_prompts,
    build_user_payload,
    evaluate_representation_audit,
)


class RunPreciseTargetMentionsV52Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        load = lambda path: json.loads(path.read_text(encoding="utf-8"))
        cls.config = load(CONFIG_PATH)
        cls.v51_config = load(V51_CONFIG_PATH)
        cls.v45_config = load(V45_CONFIG_PATH)
        cls.v44_lock = load(V44_LOCK_PATH)
        cls.dataset = load(DATASET_PATH)
        cls.rows = build_candidate_rows(cls.dataset)

    def test_frozen_inputs_validate(self):
        _validate_inputs(self.config, self.dataset)

    def test_representation_gate_passes_before_model_inference(self):
        audit = audit_precise_event_maps(
            self.rows, self.config["causal_change"]["target_mention_patterns"]
        )
        gate = evaluate_representation_audit(audit, self.config, self.rows)
        self.assertTrue(gate["passed"])
        self.assertEqual(gate["contrast_probe_observed"], {"gaze.left": "左", "gaze.right": "右"})

    def test_prompts_differ_only_by_locked_representation_instruction(self):
        prompts = build_prompts(
            self.config, self.v51_config, self.v45_config, self.v44_lock
        )
        self.assertTrue(
            prompts["v51_event_map_control"].endswith(
                self.v51_config["causal_change"]["candidate_instruction"]
            )
        )
        self.assertTrue(
            prompts["precise_target_mentions_candidate"].endswith(
                self.config["causal_change"]["candidate_instruction"]
            )
        )

    def test_both_payloads_have_one_event_map_but_different_representation(self):
        row = next(row for row in self.rows if row["case_id"] == "v45h_negation_02")
        candidate = next(
            candidate
            for candidate in row["candidates"]
            if candidate["target_id"] == "gaze.right"
        )
        control = build_user_payload(
            "v51_event_map_control",
            row,
            candidate,
            self.config,
            self.v45_config,
        )
        treatment = build_user_payload(
            "precise_target_mentions_candidate",
            row,
            candidate,
            self.config,
            self.v45_config,
        )
        self.assertEqual(set(control), set(treatment))
        control_row = control["target_event_map"]["focus_occurrences"][0]
        treatment_row = treatment["target_event_map"]["focus_occurrences"][0]
        self.assertIn("anchor_text", control_row)
        self.assertNotIn("anchor_text", treatment_row)
        self.assertIn("target_mentions", treatment_row)
        self.assertIn("predicate_evidence", treatment_row)

    def test_no_payload_contains_answer_fields(self):
        forbidden = set(self.config["causal_change"]["forbidden_fields"])
        for row in self.rows:
            for candidate in row["candidates"]:
                for condition in self.config["conditions"]:
                    payload = build_user_payload(
                        condition,
                        row,
                        candidate,
                        self.config,
                        self.v45_config,
                    )
                    self.assertTrue(forbidden.isdisjoint(payload))
                    self.assertTrue(
                        forbidden.isdisjoint(payload["target_event_map"])
                    )


if __name__ == "__main__":
    unittest.main()
