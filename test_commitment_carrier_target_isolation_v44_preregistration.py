#!/usr/bin/env python3

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "configs" / "commitment_carrier_target_isolation_v44_preregistration.json"


class CommitmentCarrierTargetIsolationV44PreregistrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = json.loads(CONFIG.read_text(encoding="utf-8"))

    def test_every_frozen_input_hash_matches(self):
        frozen = self.config["frozen_inputs"]
        for key, value in frozen.items():
            if not key.endswith("_sha256"):
                continue
            path_key = key.removesuffix("_sha256")
            path = ROOT / frozen[path_key]
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertEqual(actual, value, path.name)

    def test_format_probe_is_non_semantic_and_balanced(self):
        frozen = self.config["frozen_inputs"]
        dataset = json.loads((ROOT / frozen["format_probe_dataset"]).read_text())
        self.assertEqual(dataset["case_count"], frozen["format_probe_case_count"])
        labels = [row["source_label"] for row in dataset["cases"]]
        self.assertEqual(len(set(labels)), 6)
        self.assertTrue(all(labels.count(label) == 2 for label in set(labels)))
        self.assertFalse(self.config["stage_1_format_probe"]["contains_benchmark_language_or_inference"])

    def test_selection_and_semantic_stop_rules_are_fixed(self):
        stage_1 = self.config["stage_1_format_probe"]
        self.assertEqual(stage_1["gates"]["parse_success_rate"], 1.0)
        self.assertEqual(stage_1["gates"]["source_label_fidelity"], 1.0)
        self.assertIn("If none is eligible, stop", stage_1["selection_rule"])
        stage_2 = self.config["stage_2_semantic_conditions"]
        self.assertEqual(
            stage_2["only_candidate_allowed_to_advance"],
            "isolated_scope_signals_candidate",
        )

    def test_no_runtime_or_physical_execution_is_authorized(self):
        self.assertFalse(self.config["runtime_change_authorized"])
        self.assertFalse(self.config["shadow_integration_authorized"])
        self.assertFalse(self.config["physical_vrm_execution_enabled"])


if __name__ == "__main__":
    unittest.main()
