#!/usr/bin/env python3

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "action_intent_frame_v36_preregistration.json"


class ActionIntentFrameV36PreregistrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))

    def test_preregistration_precedes_annotation_and_inference(self):
        self.assertEqual(
            self.config["status"],
            "preregistered_before_dataset_annotation_and_before_model_inference",
        )
        self.assertFalse(self.config["runtime_change_authorized"])
        self.assertFalse(self.config["vrm_execution_enabled"])
        self.assertFalse(self.config["human_likeness_claim_authorized"])

    def test_retired_sources_are_hash_bound(self):
        source = self.config["development_source"]
        for path_key, hash_key in (
            ("dataset", "dataset_sha256"),
            ("direct_call_baselines", "direct_call_baselines_sha256"),
        ):
            path = ROOT / source[path_key]
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertEqual(digest, source[hash_key])

    def test_model_ladder_is_ordered_by_local_artifact_size(self):
        sizes = [
            condition["blob_bytes"]
            for condition in self.config["model_conditions"].values()
        ]
        self.assertEqual(sizes, sorted(sizes))
        self.assertEqual(len(sizes), 5)

    def test_frame_contract_keeps_state_commitment_and_evidence_observable(self):
        contract = self.config["frame_contract"]
        self.assertIn("explicit_current_request", contract["utterance_states"])
        self.assertIn("negated", contract["commitments"])
        self.assertIn("cancelled", contract["commitments"])
        self.assertIn("mentioned", contract["commitments"])
        self.assertIn("exact", contract["evidence_rule"])

    def test_matched_models_exist_for_representation_comparison(self):
        conditions = self.config["model_conditions"]
        self.assertIn("qwen2_5_7b_matched_reference", conditions)
        self.assertIn("qwen3_5_9b_matched_upper_reference", conditions)


if __name__ == "__main__":
    unittest.main()
