#!/usr/bin/env python3

import hashlib
import json
import unittest
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "qwen2b_binary_carrier_v50_preregistration.json"


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Qwen2BBinaryCarrierV50PreregistrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        cls.dataset = json.loads(
            (ROOT / cls.config["frozen_inputs"]["format_probe_dataset"]).read_text(
                encoding="utf-8"
            )
        )

    def test_every_input_is_hash_bound(self):
        for key, expected in self.config["frozen_inputs"].items():
            if key.endswith("_sha256"):
                self.assertEqual(
                    _sha256(ROOT / self.config["frozen_inputs"][key.removesuffix("_sha256")]),
                    expected,
                )

    def test_probe_is_balanced_and_contains_no_action_semantics(self):
        counts = Counter(row["source_decision"] for row in self.dataset["cases"])
        self.assertEqual(counts, {"execute": 6, "do_not_execute": 6})
        serialized = json.dumps(self.dataset, ensure_ascii=False).lower()
        for forbidden in ("user_input", "expected_calls", "tombench", "motion.wave"):
            self.assertNotIn(forbidden, serialized)

    def test_boolean_is_control_and_enum_two_field_is_preferred(self):
        self.assertFalse(
            self.config["carriers"]["boolean_two_field_control"]["selection_candidate"]
        )
        self.assertEqual(
            self.config["selection_priority"][0], "enum_two_field_candidate"
        )

    def test_all_calls_and_gates_are_fixed(self):
        self.assertEqual(
            self.config["expected_scored_call_count"],
            len(self.config["carrier_order"]) * self.dataset["case_count"],
        )
        self.assertEqual(self.config["gates"]["parse_success_rate"], 1.0)
        self.assertEqual(self.config["gates"]["source_decision_fidelity"], 1.0)

    def test_probe_cannot_authorize_runtime(self):
        self.assertFalse(self.config["semantic_prompt_tuning_authorized"])
        self.assertFalse(self.config["v51_fresh_holdout_construction_authorized"])
        self.assertFalse(self.config["runtime_change_authorized"])
        self.assertFalse(self.config["physical_vrm_execution_enabled"])


if __name__ == "__main__":
    unittest.main()
