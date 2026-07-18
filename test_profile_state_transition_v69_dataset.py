import hashlib
import json
import unittest
from pathlib import Path

import audit_profile_state_transition_v69_dataset as audit_module


ROOT = Path(__file__).resolve().parent


class ProfileStateTransitionV69DatasetTests(unittest.TestCase):
    def test_audit_passes_with_exact_record_counts(self):
        audit = audit_module.build_audit()
        self.assertTrue(audit["passed"], audit["failures"])
        self.assertEqual(audit["counts"]["case_count"], 18)
        self.assertEqual(audit["counts"]["expected_write_count"], 33)
        self.assertEqual(audit["counts"]["expected_active_record_count"], 21)
        self.assertEqual(audit["counts"]["expected_historical_record_count"], 12)
        self.assertEqual(set(audit["family_counts"].values()), {3})

    def test_every_expected_partition_covers_written_turns_once(self):
        dataset = json.loads((ROOT / "datasets/profile_state_transition_v69.json").read_text(encoding="utf-8"))
        for case in dataset["cases"]:
            expected = case["expected"]
            active = set(expected["active_turn_ids"])
            historical = set(expected["historical_turn_ids"])
            self.assertFalse(active & historical)
            self.assertEqual(active | historical, set(expected["written_turn_ids"]))

    def test_primary_comparison_changes_only_state_metadata(self):
        prereg = json.loads((ROOT / "configs/profile_state_transition_v69_preregistration.json").read_text(encoding="utf-8"))
        self.assertIn("metadata", prereg["only_changed_component_for_primary_comparison"])
        self.assertFalse(prereg["authorizations"]["candidate_implementation"])
        self.assertFalse(prereg["authorizations"]["production_database_access"])

    def test_closure_binds_inputs_and_forbids_shadow(self):
        closure = json.loads((ROOT / "configs/profile_state_transition_v69_dataset_closure.json").read_text(encoding="utf-8"))
        paths = {"preregistration": "configs/profile_state_transition_v69_preregistration.json", "dataset": "datasets/profile_state_transition_v69.json", "audit": "reports/profile_state_transition_v69_dataset_audit.json"}
        for name, relative in paths.items():
            self.assertEqual(closure["frozen_artifacts"][name], hashlib.sha256((ROOT / relative).read_bytes()).hexdigest())
        self.assertTrue(closure["authorizations"]["candidate_implementation"])
        self.assertFalse(closure["authorizations"]["shadow_execution"])


if __name__ == "__main__":
    unittest.main()
