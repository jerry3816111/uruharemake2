#!/usr/bin/env python3

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
LOCK_PATH = ROOT / "configs" / "commitment_target_isolation_v44_semantic_lock.json"


class CommitmentTargetIsolationV44SemanticLockTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))

    def test_selection_and_semantic_input_hashes_match(self):
        for section in ("selection_provenance", "frozen_semantic_inputs"):
            values = self.lock[section]
            for key, expected in values.items():
                if not key.endswith("_sha256"):
                    continue
                path = ROOT / values[key.removesuffix("_sha256")]
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), expected)
        analysis = json.loads(
            (ROOT / self.lock["selection_provenance"]["carrier_probe_analysis"]).read_text()
        )
        self.assertEqual(
            analysis["selected_carrier"],
            self.lock["selection_provenance"]["selected_carrier"],
        )

    def test_each_condition_changes_only_the_declared_next_layer(self):
        payloads = self.lock["condition_payloads"]
        self.assertEqual(
            set(payloads["all_targets_relational"]) - set(payloads["target_only_control"]),
            {"all_grounded_targets"},
        )
        self.assertEqual(
            set(payloads["isolated_scope_signals_candidate"])
            - set(payloads["isolated_other_targets"]),
            {"focus_anchor_scope_signals"},
        )

    def test_prompts_contain_no_lexical_action_examples_or_gold_fields(self):
        prompt_text = " ".join(
            self.lock[key]
            for key in (
                "base_instruction",
                "relational_instruction",
                "target_isolation_instruction",
                "scope_signal_instruction",
            )
        )
        for forbidden in ("手を振", "うなず", "笑った顔", "expected_calls", "gold"):
            self.assertNotIn(forbidden, prompt_text)
        self.assertFalse(self.lock["gold_or_expected_fields_allowed_in_model_input"])

    def test_only_final_condition_can_advance_and_execution_is_disabled(self):
        self.assertEqual(
            self.lock["only_candidate_allowed_to_advance"],
            "isolated_scope_signals_candidate",
        )
        self.assertFalse(self.lock["runtime_change_authorized"])
        self.assertFalse(self.lock["shadow_integration_authorized"])
        self.assertFalse(self.lock["physical_vrm_execution_enabled"])


if __name__ == "__main__":
    unittest.main()
