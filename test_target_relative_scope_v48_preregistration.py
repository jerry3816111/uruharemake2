#!/usr/bin/env python3

import hashlib
import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "target_relative_scope_v48_preregistration.json"


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class TargetRelativeScopeV48PreregistrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))

    def test_all_historical_inputs_are_hash_bound(self):
        frozen = self.config["frozen_inputs"]
        for key, expected in frozen.items():
            if key.endswith("_sha256"):
                self.assertEqual(_sha256(ROOT / frozen[key.removesuffix("_sha256")]), expected)

    def test_negative_suffix_does_not_match_lexical_nod_stem(self):
        pattern = re.compile(self.config["causal_change"]["negative_suffix_pattern"])
        self.assertIsNone(pattern.search("うなずいて"))
        self.assertIsNotNone(pattern.search("うなずかずに"))
        self.assertIsNotNone(pattern.search("うなずかないで"))

    def test_probes_cover_spillover_correction_cessation_and_suffix(self):
        probe_ids = {row["id"] for row in self.config["metamorphic_probes"]}
        self.assertEqual(len(probe_ids), 6)
        self.assertIn("alternative_same_clause", probe_ids)
        self.assertIn("same_target_late_positive_correction", probe_ids)
        self.assertIn("cessation_then_replacement", probe_ids)
        self.assertIn("negative_suffix_inside_nod_verb", probe_ids)

    def test_gate_requires_complete_scope_and_compiler_correctness(self):
        gates = self.config["development_gates"]
        self.assertEqual(gates["requested_target_safe_anchor_recall"], 1.0)
        self.assertEqual(gates["negated_target_blocked_all_recall"], 1.0)
        self.assertEqual(gates["cancelled_target_blocked_all_recall"], 1.0)
        self.assertEqual(gates["perfect_semantic_compiled_call_exact_accuracy"], 1.0)
        self.assertEqual(gates["perfect_semantic_false_action_rate"], 0.0)

    def test_no_runtime_change_is_preauthorized(self):
        self.assertFalse(self.config["runtime_change_authorized"])
        self.assertFalse(self.config["shadow_integration_authorized"])
        self.assertFalse(self.config["physical_vrm_execution_enabled"])


if __name__ == "__main__":
    unittest.main()
