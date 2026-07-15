#!/usr/bin/env python3

import json
import unittest

from run_target_event_map_v51 import (
    CONFIG_PATH,
    DATASET_PATH,
    V44_LOCK_PATH,
    V45_CONFIG_PATH,
    _validate_inputs,
    build_candidate_rows,
    build_prompts,
    build_user_payload,
)


class RunTargetEventMapV51Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        load = lambda path: json.loads(path.read_text(encoding="utf-8"))
        cls.config = load(CONFIG_PATH)
        cls.v45_config = load(V45_CONFIG_PATH)
        cls.v44_lock = load(V44_LOCK_PATH)
        cls.dataset = load(DATASET_PATH)
        cls.rows = build_candidate_rows(cls.dataset)

    def test_frozen_inputs_validate(self):
        _validate_inputs(self.config, self.dataset)

    def test_grounded_target_count_is_fixed(self):
        self.assertEqual(
            sum(len(row["candidates"]) for row in self.rows),
            self.config["frozen_inputs"]["grounded_target_count"],
        )

    def test_only_candidate_prompt_adds_the_locked_instruction(self):
        prompts = build_prompts(self.config, self.v45_config, self.v44_lock)
        instruction = self.config["causal_change"]["candidate_instruction"]
        self.assertNotIn(instruction, prompts["v48_six_way_control"])
        self.assertTrue(prompts["target_event_map_candidate"].endswith(instruction))

    def test_only_candidate_payload_adds_event_map(self):
        row = self.rows[0]
        candidate = row["candidates"][0]
        control = build_user_payload(
            "v48_six_way_control",
            row,
            candidate,
            self.config,
            self.v45_config,
        )
        treatment = build_user_payload(
            "target_event_map_candidate",
            row,
            candidate,
            self.config,
            self.v45_config,
        )
        self.assertNotIn("target_event_map", control)
        self.assertEqual(set(treatment), set(control) | {"target_event_map"})

    def test_payload_never_contains_gold_or_execution_answer(self):
        forbidden = set(self.config["causal_change"]["forbidden_fields"])
        for row in self.rows:
            for candidate in row["candidates"]:
                payload = build_user_payload(
                    "target_event_map_candidate",
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
