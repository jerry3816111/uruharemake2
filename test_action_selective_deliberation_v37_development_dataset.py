#!/usr/bin/env python3

import hashlib
import json
import unittest
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SOURCE_PATH = ROOT / "datasets" / "action_intent_frame_v36_development.json"
DATASET_PATH = ROOT / "datasets" / "action_selective_deliberation_v37_development.json"
FREEZE_PATH = ROOT / "configs" / "action_selective_deliberation_v37_dataset_freeze.json"


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ActionSelectiveDeliberationV37DatasetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = json.loads(SOURCE_PATH.read_text(encoding="utf-8"))
        cls.dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
        cls.freeze = json.loads(FREEZE_PATH.read_text(encoding="utf-8"))

    def test_dataset_is_exactly_the_retired_36_case_source(self):
        self.assertEqual(self.dataset["case_count"], 36)
        self.assertEqual(self.dataset["evidence_status"], "retired_development_only_converted_from_v36")
        self.assertEqual(self.dataset["source_dataset_sha256"], _sha256(SOURCE_PATH))
        self.assertEqual(
            [case["id"] for case in self.dataset["cases"]],
            [case["id"] for case in self.source["cases"]],
        )

    def test_user_inputs_and_expected_calls_are_unchanged(self):
        source_by_id = {case["id"]: case for case in self.source["cases"]}
        for case in self.dataset["cases"]:
            source = source_by_id[case["id"]]
            self.assertEqual(case["user_input"], source["user_input"])
            self.assertEqual(case["expected_calls"], source["expected_calls"])
            self.assertEqual(case["forbidden_calls"], source["forbidden_calls"])
            self.assertEqual(case["expected_no_action"], source["expected_no_action"])

    def test_unsupported_is_an_attribute_not_a_synthetic_frame(self):
        unsupported = [
            frame
            for case in self.dataset["cases"]
            for frame in case["expected_frames"]
            if frame["value"] == "unsupported"
        ]
        self.assertEqual(len(unsupported), 6)
        self.assertTrue(all(frame["domain"] in {"motion", "other"} for frame in unsupported))
        self.assertTrue(all(frame["commitment"] == "requested" for frame in unsupported))
        self.assertNotIn("unsupported", {frame["domain"] for frame in unsupported})

    def test_balanced_families_and_independent_risk_labels(self):
        counts = Counter(case["family"] for case in self.dataset["cases"])
        self.assertEqual(set(counts.values()), {6})
        self.assertEqual(sum(case["expected_deliberation"] for case in self.dataset["cases"]), 20)

    def test_freeze_hashes_current_artifacts_before_inference(self):
        self.assertEqual(self.freeze["dataset_sha256"], _sha256(DATASET_PATH))
        self.assertEqual(self.freeze["source_dataset_sha256"], _sha256(SOURCE_PATH))
        self.assertEqual(self.freeze["case_count"], 36)
        self.assertFalse(self.freeze["inference_performed_before_freeze"])


if __name__ == "__main__":
    unittest.main()
