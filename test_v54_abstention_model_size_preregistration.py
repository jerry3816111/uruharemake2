#!/usr/bin/env python3

import hashlib
import json
import unittest
from pathlib import Path

from build_v54_abstention_model_size_dataset import build


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "v54_abstention_model_size_preregistration.json"
DATASET_PATH = ROOT / "datasets" / "v54_abstention_model_size_holdout.json"


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class V54AbstentionModelSizePreregistrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        cls.dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))

    def test_every_local_frozen_input_is_hash_bound(self):
        frozen = self.config["frozen_inputs"]
        for key, expected in frozen.items():
            if not key.endswith("_sha256"):
                continue
            path = ROOT / frozen[key.removesuffix("_sha256")]
            self.assertEqual(_sha256(path), expected, path)

    def test_subset_is_exactly_the_mechanical_v54_abstentions(self):
        self.assertEqual(build(), self.dataset)
        self.assertEqual(self.dataset["item_count"], 10)
        self.assertTrue(self.dataset["construction"]["selection_is_mechanical"])
        self.assertFalse(self.dataset["construction"]["new_model_inference_used"])

    def test_subset_is_balanced_and_binds_frozen_4b_result(self):
        self.assertEqual(
            self.dataset["gold_commitment_counts"],
            {"mentioned": 5, "requested": 5},
        )
        self.assertEqual(self.dataset["frozen_4b_correct_count"], 8)

    def test_four_local_sizes_share_generation_controls(self):
        models = self.config["model_conditions"]
        self.assertEqual(len(models), 4)
        fixed = {
            (
                row["temperature"],
                row["top_p"],
                row["seed"],
                row["context_tokens"],
                row["maximum_output_tokens"],
                row["thinking"],
            )
            for row in models.values()
        }
        self.assertEqual(len(fixed), 1)
        self.assertTrue(all(not row["paid_api"] for row in models.values()))

    def test_candidate_must_improve_without_false_request_or_regression(self):
        gates = self.config["candidate_gates"]
        self.assertEqual(gates["accuracy_at_least"], 0.9)
        self.assertEqual(gates["requested_false_positive_count"], 0)
        self.assertEqual(gates["fixed_count_at_least"], 1)
        self.assertEqual(gates["regression_count_at_most"], 0)

    def test_diagnostic_cannot_replace_runtime_fallback(self):
        self.assertFalse(self.config["fallback_replacement_authorized"])
        self.assertFalse(self.config["runtime_change_authorized"])
        self.assertFalse(self.config["shadow_integration_authorized"])
        self.assertFalse(self.config["physical_vrm_execution_enabled"])


if __name__ == "__main__":
    unittest.main()
