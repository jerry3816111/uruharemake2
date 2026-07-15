#!/usr/bin/env python3

import hashlib
import json
import unittest
from pathlib import Path

from build_predicate_morphology_v60_independent_holdout import build


ROOT = Path(__file__).resolve().parent
CLOSURE_PATH = (
    ROOT
    / "configs"
    / "predicate_morphology_v60_independent_holdout_construction_closure.json"
)


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class PredicateMorphologyV60IndependentHoldoutConstructionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.closure = json.loads(CLOSURE_PATH.read_text(encoding="utf-8"))
        bindings = cls.closure["artifact_bindings"]
        cls.dataset = json.loads(
            (ROOT / bindings["dataset"]).read_text(encoding="utf-8")
        )
        cls.audit = json.loads(
            (ROOT / bindings["audit_json"]).read_text(encoding="utf-8")
        )

    def test_every_construction_artifact_is_hash_bound(self):
        bindings = self.closure["artifact_bindings"]
        for key, expected in bindings.items():
            if not key.endswith("_sha256"):
                continue
            path_key = key.removesuffix("_sha256")
            self.assertEqual(_sha256(ROOT / bindings[path_key]), expected, path_key)

    def test_builder_reproduces_the_frozen_dataset(self):
        self.assertEqual(build(), self.dataset)

    def test_counts_and_provenance_match_closure(self):
        result = self.closure["construction_result"]
        self.assertEqual(self.dataset["case_count"], result["case_count"])
        self.assertEqual(
            self.dataset["grounded_target_count"], result["grounded_target_count"]
        )
        self.assertEqual(self.dataset["source_counts"]["external_exact"], 19)
        self.assertEqual(
            self.dataset["source_counts"]["controlled_researcher_authored"], 98
        )
        self.assertFalse(
            self.dataset["construction"]["base_model_pretraining_exclusion_guaranteed"]
        )

    def test_construction_audit_passed_without_overlap_or_grounding_failure(self):
        self.assertTrue(self.audit["passed"])
        self.assertTrue(all(self.audit["checks"].values()))
        self.assertEqual(self.audit["grounding_failures"], [])
        self.assertEqual(self.audit["historical_exact_overlaps"], [])
        self.assertEqual(self.audit["historical_near_overlaps"], [])
        self.assertEqual(self.audit["internal_exact_duplicates"], [])

    def test_first_failure_and_corrections_are_not_hidden(self):
        log = self.closure["pre_evaluation_correction_log"]
        self.assertEqual(log["first_audit_status"], "failed")
        self.assertEqual(log["first_failure_count"], 3)
        self.assertEqual(len(log["corrections"]), 5)
        self.assertFalse(log["v59_state_evaluated_before_correction"])
        self.assertFalse(log["v60_state_evaluated_before_correction"])
        self.assertFalse(log["model_inference_used_before_correction"])
        self.assertFalse(log["score_gate_relaxed"])

    def test_construction_code_contains_no_evaluator_or_model_transport(self):
        bindings = self.closure["artifact_bindings"]
        source = "\n".join(
            (ROOT / bindings[key]).read_text(encoding="utf-8")
            for key in ("builder", "auditor")
        )
        for forbidden in (
            "resolve_v59",
            "resolve_v60",
            "compile_relation_authorized_v57",
            "_call_ollama",
            "urllib.request",
            "requests.post",
        ):
            self.assertNotIn(forbidden, source)

    def test_only_evaluator_preregistration_is_authorized(self):
        self.assertEqual(
            self.closure["decision"],
            "authorize_v60_independent_evaluator_preregistration_only",
        )
        self.assertFalse(self.closure["model_or_state_evaluation_performed"])
        for key in (
            "runtime_change_authorized",
            "shadow_integration_authorized",
            "physical_vrm_execution_enabled",
            "complete_rightbrain_claim_authorized",
            "broad_human_likeness_claim_authorized",
        ):
            self.assertFalse(self.closure[key], key)


if __name__ == "__main__":
    unittest.main()
