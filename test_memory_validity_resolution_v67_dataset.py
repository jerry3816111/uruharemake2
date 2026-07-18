import hashlib
import json
import unittest
from pathlib import Path

import audit_memory_validity_resolution_v67_dataset as audit_module


ROOT = Path(__file__).resolve().parent


class MemoryValidityResolutionV67DatasetTests(unittest.TestCase):
    def test_audit_passes_with_balanced_fresh_cases(self):
        audit = audit_module.build_audit()
        self.assertTrue(audit["passed"], audit["failures"])
        self.assertEqual(audit["counts"]["case_count"], 18)
        self.assertEqual(audit["counts"]["scenario_family_count"], 6)
        self.assertEqual(set(audit["family_counts"].values()), {3})

    def test_expected_partitions_cover_every_candidate_once(self):
        dataset = json.loads((ROOT / "datasets/memory_validity_resolution_v67.json").read_text(encoding="utf-8"))
        for case in dataset["cases"]:
            candidate_ids = {row["memory_id"] for row in case["candidates"]}
            expected = case["expected"]
            partitions = [set(expected[key]) for key in ("eligible_ids", "historical_ids", "inapplicable_ids")]
            self.assertFalse(partitions[0] & partitions[1])
            self.assertFalse(partitions[0] & partitions[2])
            self.assertFalse(partitions[1] & partitions[2])
            self.assertEqual(set().union(*partitions), candidate_ids)
            self.assertEqual(set(expected["working_memory_ids"]), partitions[0])

    def test_preregistration_forbids_case_specific_or_runtime_changes(self):
        prereg = json.loads((ROOT / "configs/memory_validity_resolution_v67_preregistration.json").read_text(encoding="utf-8"))
        self.assertIn("case IDs", " ".join(prereg["stop_conditions"]))
        self.assertFalse(prereg["authorizations"]["candidate_implementation"])
        self.assertFalse(prereg["authorizations"]["runtime_change"])
        self.assertEqual(prereg["only_changed_component"], "whether a temporal and contextual validity resolver runs before the existing salience ranker")

    def test_closure_binds_frozen_inputs_and_forbids_pilot(self):
        closure = json.loads((ROOT / "configs/memory_validity_resolution_v67_dataset_closure.json").read_text(encoding="utf-8"))
        paths = {
            "preregistration": "configs/memory_validity_resolution_v67_preregistration.json",
            "dataset": "datasets/memory_validity_resolution_v67.json",
            "audit": "reports/memory_validity_resolution_v67_dataset_audit.json",
        }
        for name, relative in paths.items():
            self.assertEqual(closure["frozen_artifacts"][name], hashlib.sha256((ROOT / relative).read_bytes()).hexdigest())
        self.assertTrue(closure["authorizations"]["candidate_implementation"])
        self.assertFalse(closure["authorizations"]["pilot_execution"])


if __name__ == "__main__":
    unittest.main()
