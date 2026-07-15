#!/usr/bin/env python3

import hashlib
import json
import subprocess
import unittest
from collections import Counter
from pathlib import Path

from build_event_role_governor_v59_holdout import build


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = (
    ROOT
    / "configs"
    / "event_role_governor_v59_holdout_construction_preregistration.json"
)
CLOSURE_PATH = (
    ROOT / "configs" / "event_role_governor_v59_holdout_construction_closure.json"
)
DATASET_PATH = ROOT / "datasets" / "event_role_governor_v59_holdout.json"
AUDIT_PATH = ROOT / "reports" / "event_role_governor_v59_holdout_audit.json"


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class EventRoleGovernorV59HoldoutConstructionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        load = lambda path: json.loads(path.read_text(encoding="utf-8"))
        cls.config = load(CONFIG_PATH)
        cls.closure = load(CLOSURE_PATH)
        cls.dataset = load(DATASET_PATH)
        cls.audit = load(AUDIT_PATH)

    def test_every_construction_artifact_and_dependency_is_hash_bound(self):
        bindings = self.closure["artifact_bindings"]
        for key, expected in bindings.items():
            if not key.endswith("_sha256"):
                continue
            path_key = key.removesuffix("_sha256")
            self.assertIn(path_key, bindings)
            self.assertEqual(_sha256(ROOT / bindings[path_key]), expected, path_key)

    def test_original_preregistration_is_preserved_in_git_history(self):
        original = self.closure["original_preregistration"]
        payload = subprocess.check_output(
            [
                "git",
                "show",
                f"{original['commit']}:configs/event_role_governor_v59_holdout_construction_preregistration.json",
            ],
            cwd=ROOT,
        )
        self.assertEqual(hashlib.sha256(payload).hexdigest(), original["sha256"])

    def test_builder_reproduces_frozen_dataset(self):
        self.assertEqual(build(), self.dataset)

    def test_balanced_matrix_and_nontrivial_action_labels_are_exact(self):
        self.assertEqual(self.dataset["case_count"], 72)
        self.assertEqual(
            self.dataset["source_counts"],
            {"controlled_researcher_authored": 56, "external_exact": 16},
        )
        controlled_counts = Counter(
            case["family"]
            for case in self.dataset["cases"]
            if case["source_type"] == "controlled_researcher_authored"
        )
        self.assertEqual(set(controlled_counts.values()), {14})
        self.assertEqual(len(controlled_counts), 4)
        self.assertEqual(sum(not case["expected_no_action"] for case in self.dataset["cases"]), 14)
        self.assertEqual(sum(case["expected_no_action"] for case in self.dataset["cases"]), 58)

    def test_frozen_audit_passed_every_gate_without_overlap(self):
        self.assertTrue(self.audit["passed"])
        self.assertEqual(self.audit["failed_checks"], [])
        self.assertTrue(all(self.audit["checks"].values()))
        self.assertEqual(self.audit["historical_exact_input_overlap_count"], 0)
        self.assertEqual(self.audit["historical_near_duplicate_count"], 0)
        self.assertEqual(self.audit["prior_external_source_id_overlap_count"], 0)
        self.assertLess(self.audit["maximum_historical_similarity"], 0.94)
        self.assertEqual(self.audit["representation_audit"]["fallback_occurrence_count"], 0)

    def test_first_failed_audit_and_both_pre_evaluation_repairs_are_disclosed(self):
        amendment = self.config["construction_amendment"]
        correction = self.closure["pre_evaluation_correction_log"]
        self.assertEqual(amendment["first_audit_failed_checks"], ["candidate_target_sets_exact"])
        self.assertEqual(correction["first_failed_checks"], ["candidate_target_sets_exact"])
        self.assertEqual(len(amendment["corrections"]), 2)
        self.assertEqual(len(correction["corrections"]), 2)
        self.assertEqual(
            {row["slot"] for row in correction["corrections"]},
            {
                "external_exact_expression_happy",
                "controlled_direct_focus_request_contrast.expression.happy",
            },
        )
        for key in (
            "v58_state_evaluated_before_correction",
            "v59_state_evaluated_before_correction",
            "compiler_evaluated_before_correction",
            "model_inference_used_before_correction",
            "score_gate_or_family_changed",
        ):
            self.assertFalse(amendment[key], key)

    def test_provenance_and_construction_firewall_are_honest(self):
        construction = self.dataset["construction"]
        self.assertFalse(construction["controlled_model_assistance_used"])
        self.assertFalse(construction["controlled_human_blind_review_used"])
        self.assertFalse(construction["evaluation_model_inference_used"])
        self.assertFalse(construction["v58_state_evaluation_used"])
        self.assertFalse(construction["v59_state_evaluation_used"])
        self.assertFalse(construction["compiler_evaluation_used"])
        self.assertFalse(construction["base_model_pretraining_exclusion_guaranteed"])
        for case in self.dataset["cases"]:
            provenance = case["source_provenance"]
            if case["source_type"] == "external_exact":
                self.assertIn("tatoeba.org/en/sentences/show/", provenance["sentence_url"])
            else:
                self.assertFalse(provenance["model_assistance_used"])
                self.assertFalse(provenance["human_blind_review_used"])
                self.assertFalse(provenance["official_corpus_claimed"])

    def test_construction_code_cannot_evaluate_v58_v59_compiler_or_model(self):
        source = (
            (ROOT / "build_event_role_governor_v59_holdout.py").read_text(encoding="utf-8")
            + (ROOT / "audit_event_role_governor_v59_holdout.py").read_text(encoding="utf-8")
        )
        for forbidden in (
            "resolve_v58",
            "resolve_v59",
            "compile_v57",
            "_run_judgment",
            "urllib.request",
            "requests.post",
            "localhost:11434",
        ):
            self.assertNotIn(forbidden, source)

    def test_pass_authorizes_only_the_next_preregistration(self):
        self.assertEqual(
            self.closure["decision"],
            "authorize_independent_v59_evaluator_preregistration_only",
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
