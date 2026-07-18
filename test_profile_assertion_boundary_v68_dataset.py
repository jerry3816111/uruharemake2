import hashlib
import json
import unittest
from pathlib import Path

import audit_profile_assertion_boundary_v68_dataset as audit_module


ROOT = Path(__file__).resolve().parent


class ProfileAssertionBoundaryV68DatasetTests(unittest.TestCase):
    def test_audit_passes_with_balanced_positive_and_negative_cases(self):
        audit = audit_module.build_audit()
        self.assertTrue(audit["passed"], audit["failures"])
        self.assertEqual(audit["counts"]["case_count"], 24)
        self.assertEqual(audit["counts"]["positive_assertion_count"], 12)
        self.assertEqual(audit["counts"]["non_assertion_count"], 12)
        self.assertEqual(set(audit["family_counts"].values()), {4})

    def test_expected_facts_are_separate_from_utterances(self):
        dataset = json.loads((ROOT / "datasets/profile_assertion_boundary_v68.json").read_text(encoding="utf-8"))
        for case in dataset["cases"]:
            self.assertNotIn("expected", case["utterance"].casefold())
            facts = {(row["fact_type"], row["value"].casefold()) for row in case["expected_facts"]}
            self.assertEqual(len(facts), len(case["expected_facts"]))

    def test_preregistration_changes_only_assertion_scope(self):
        prereg = json.loads((ROOT / "configs/profile_assertion_boundary_v68_preregistration.json").read_text(encoding="utf-8"))
        self.assertEqual(prereg["only_changed_component"], "whether extracted facts must pass a direct user profile assertion scope guard")
        self.assertFalse(prereg["authorizations"]["candidate_implementation"])
        self.assertFalse(prereg["authorizations"]["persistent_memory_access"])

    def test_closure_binds_inputs_and_forbids_pilot(self):
        closure = json.loads((ROOT / "configs/profile_assertion_boundary_v68_dataset_closure.json").read_text(encoding="utf-8"))
        paths = {
            "preregistration": "configs/profile_assertion_boundary_v68_preregistration.json",
            "dataset": "datasets/profile_assertion_boundary_v68.json",
            "audit": "reports/profile_assertion_boundary_v68_dataset_audit.json"
        }
        for name, relative in paths.items():
            self.assertEqual(closure["frozen_artifacts"][name], hashlib.sha256((ROOT / relative).read_bytes()).hexdigest())
        self.assertTrue(closure["authorizations"]["candidate_implementation"])
        self.assertFalse(closure["authorizations"]["pilot_execution"])


if __name__ == "__main__":
    unittest.main()
