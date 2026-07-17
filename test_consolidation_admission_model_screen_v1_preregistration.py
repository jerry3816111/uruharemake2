#!/usr/bin/env python3
"""Validate the V1 consolidation-admission model screen preregistration."""

from __future__ import annotations

import hashlib
import json
import subprocess
import unittest
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = (
    ROOT
    / "configs"
    / "consolidation_admission_model_screen_v1_development_preregistration.json"
)
DATASET_PATH = (
    ROOT
    / "datasets"
    / "consolidation_admission_model_screen_v1_development.json"
)
V3_CONFIG_PATH = (
    ROOT
    / "configs"
    / "consolidation_admission_v3_role_separated_development_preregistration.json"
)
V3_RESULT_LOCK_PATH = (
    ROOT
    / "configs"
    / "consolidation_admission_v3_role_separated_result_lock.json"
)
V46_ANALYSIS_PATH = (
    ROOT / "reports" / "commitment_model_capacity_v46_development_analysis.md"
)
PRIOR_DATASET_PATHS = (
    ROOT / "datasets" / "consolidation_admission_v1_development.json",
    ROOT / "datasets" / "consolidation_admission_v2_indexed_development.json",
    ROOT
    / "datasets"
    / "consolidation_admission_v3_role_separated_development.json",
)
RESULT_PATHS = (
    ROOT
    / "reports"
    / "consolidation_admission_model_screen_v1_development_raw.json",
    ROOT
    / "reports"
    / "consolidation_admission_model_screen_v1_development_analysis.json",
    ROOT
    / "reports"
    / "consolidation_admission_model_screen_v1_development_analysis.md",
    ROOT
    / "configs"
    / "consolidation_admission_model_screen_v1_result_lock.json",
)
RESULT_LOCK_PATH = (
    ROOT
    / "configs"
    / "consolidation_admission_model_screen_v1_result_lock.json"
)


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ConsolidationAdmissionModelScreenV1PreregistrationTest(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls):
        cls.config = _load(CONFIG_PATH)
        cls.dataset = _load(DATASET_PATH)
        cls.v3_config = _load(V3_CONFIG_PATH)

    def test_experiment_identity_and_dataset_hash_are_stable(self):
        self.assertEqual(
            self.config["experiment_id"],
            "consolidation_admission_model_screen_v1_development",
        )
        self.assertEqual(self.config["dataset"]["sha256"], _sha256(DATASET_PATH))
        self.assertEqual(len(self.dataset["cases"]), 12)

    def test_dataset_is_balanced_unique_and_not_translated(self):
        cases = self.dataset["cases"]
        self.assertEqual(
            Counter(case["language"] for case in cases),
            Counter({"eng": 4, "jpn": 4, "cmn": 4}),
        )
        self.assertEqual(
            Counter(case["expected_memory_kind"] for case in cases),
            Counter({"wisdom": 4, "procedural": 4, "none": 4}),
        )
        self.assertEqual(
            Counter(case["expected_persistence_basis"] for case in cases),
            Counter(
                {
                    "stable_trait": 2,
                    "repeated_pattern": 2,
                    "explicit_future_policy": 4,
                    "no_long_term_basis": 4,
                }
            ),
        )
        self.assertEqual(len({case["id"] for case in cases}), 12)
        self.assertEqual(len({case["scenario_family"] for case in cases}), 12)
        self.assertFalse(self.dataset["semantic_translation_pairs_present"])
        self.assertFalse(self.dataset["official_source_labels"])
        self.assertFalse(self.dataset["independent_human_label_validation"])
        self.assertFalse(
            self.dataset["model_inference_used_during_construction"]
        )

    def test_gold_frames_and_evidence_indices_are_structurally_valid(self):
        applies_to = {
            "wisdom": "user_profile",
            "procedural": "assistant_policy",
            "none": "none",
        }
        for case in self.dataset["cases"]:
            self.assertEqual(len(case["session"]), 3)
            self.assertEqual(
                case["expected_applies_to"],
                applies_to[case["expected_memory_kind"]],
            )
            required = case["required_evidence_user_turns"]
            allowed = case["allowed_evidence_user_turns"]
            self.assertEqual(len(required), len(set(required)))
            self.assertEqual(len(allowed), len(set(allowed)))
            self.assertTrue(
                all(index in {1, 2, 3} for index in required + allowed)
            )
            self.assertTrue(set(required) <= set(allowed))
            if case["expected_memory_kind"] == "none":
                self.assertEqual(
                    case["expected_persistence_basis"],
                    "no_long_term_basis",
                )
                self.assertEqual(required, [])
                self.assertEqual(allowed, [])
            else:
                self.assertTrue(required)
            if case["expected_persistence_basis"] == "repeated_pattern":
                self.assertGreaterEqual(len(required), 2)
            if case["expected_memory_kind"] == "procedural":
                self.assertEqual(
                    case["expected_persistence_basis"],
                    "explicit_future_policy",
                )

    def test_no_user_utterance_or_scenario_overlap_with_v1_v2_or_v3(self):
        current = {
            turn["user"].strip().casefold()
            for case in self.dataset["cases"]
            for turn in case["session"]
        }
        current_families = {
            case["scenario_family"] for case in self.dataset["cases"]
        }
        prior = set()
        prior_families = set()
        for path in PRIOR_DATASET_PATHS:
            payload = _load(path)
            prior.update(
                turn["user"].strip().casefold()
                for case in payload["cases"]
                for turn in case["session"]
            )
            prior_families.update(
                case["scenario_family"]
                for case in payload["cases"]
                if "scenario_family" in case
            )
        self.assertEqual(current & prior, set())
        self.assertEqual(current_families & prior_families, set())
        overlap_audit = self.config["dataset"]["prior_overlap_audit"]
        self.assertEqual(
            overlap_audit["exact_user_utterance_overlap_v1_v2_v3"], 0
        )
        self.assertEqual(overlap_audit["scenario_family_overlap_v2_v3"], 0)
        self.assertIn(
            "v1_schema_has_no_scenario_family_field",
            overlap_audit["v1_scenario_family_machine_check"],
        )

    def test_v3_failure_is_hash_bound_and_not_retested(self):
        dependency = self.config["v3_dependency"]
        self.assertEqual(
            dependency["result_lock_sha256"], _sha256(V3_RESULT_LOCK_PATH)
        )
        self.assertEqual(
            dependency["preregistration_sha256"], _sha256(V3_CONFIG_PATH)
        )
        self.assertEqual(dependency["result"], "FAIL")
        self.assertFalse(dependency["same_dataset_retest_authorized"])
        self.assertNotEqual(
            self.config["dataset"]["sha256"],
            self.v3_config["dataset"]["sha256"],
        )

    def test_prior_capacity_evidence_is_hash_bound(self):
        evidence = next(
            item
            for item in self.config["existing_evidence"]
            if item.get("path")
            == "reports/commitment_model_capacity_v46_development_analysis.md"
        )
        self.assertEqual(evidence["sha256"], _sha256(V46_ANALYSIS_PATH))

    def test_contract_is_exact_frozen_v3_candidate(self):
        source = self.v3_config["conditions"][
            "v3_role_separated_tool_candidate"
        ]
        fixed = self.config["fixed_v3_contract"]
        self.assertEqual(fixed["system_prompt"], source["system_prompt"])
        self.assertEqual(fixed["tool_contract"], source["tool_contract"])
        self.assertEqual(
            fixed["deterministic_compiler"],
            source["deterministic_compiler"],
        )
        generation = dict(self.config["generation"])
        generation.pop("transport_attempts")
        source_generation = dict(self.v3_config["generation"])
        source_generation.pop("transport_attempts")
        self.assertEqual(generation, source_generation)
        self.assertEqual(self.config["generation"]["transport_attempts"], 1)

    def test_only_model_artifact_changes_between_conditions(self):
        models = self.config["models"]
        self.assertEqual(
            set(models),
            {
                "qwen25_7b_control",
                "qwen35_4b_candidate",
                "qwen35_9b_candidate",
            },
        )
        self.assertEqual(
            {len(model["digest"]) for model in models.values()}, {64}
        )
        self.assertEqual(
            len({model["digest"] for model in models.values()}), 3
        )
        self.assertEqual(
            self.config["only_changed_component"],
            "ollama_model_tag_and_corresponding_frozen_model_artifact",
        )
        self.assertIn("system_prompt", self.config["fixed_components"])
        self.assertIn("tool_contract", self.config["fixed_components"])
        self.assertIn(
            "deterministic_compiler", self.config["fixed_components"]
        )
        self.assertIn("generation_settings", self.config["fixed_components"])

    def test_latin_square_order_is_balanced(self):
        order = self.config["condition_order"]
        rows = [
            order["case_index_mod_3_equals_0"],
            order["case_index_mod_3_equals_1"],
            order["case_index_mod_3_equals_2"],
        ]
        model_ids = set(self.config["models"])
        for row in rows:
            self.assertEqual(set(row), model_ids)
        for position in range(3):
            self.assertEqual(
                {row[position] for row in rows},
                model_ids,
            )

    def test_contract_contains_no_case_text_or_gold(self):
        fixed = self.config["fixed_v3_contract"]
        serialized = json.dumps(fixed, ensure_ascii=False)
        for case in self.dataset["cases"]:
            self.assertNotIn(case["id"], serialized)
            self.assertNotIn(case["session"][0]["user"], serialized)
            self.assertNotIn(case["gold_reason"], serialized)
        for forbidden in (
            "expected_memory_kind",
            "expected_persistence_basis",
            "expected_applies_to",
            "required_evidence_user_turns",
            "allowed_evidence_user_turns",
        ):
            self.assertNotIn(forbidden, serialized)

    def test_gates_require_semantics_safety_pairwise_gain_and_contract(self):
        gates = self.config["eligibility_gates"]
        self.assertGreaterEqual(gates["candidate_correct_count_min"], 10)
        for target in ("wisdom", "procedural", "none"):
            self.assertGreaterEqual(
                gates[f"candidate_{target}_correct_min"], 3
            )
        self.assertGreaterEqual(
            gates["candidate_semantic_frame_exact_count_min"], 10
        )
        self.assertGreaterEqual(
            gates["candidate_positive_evidence_grounded_count_min"], 6
        )
        self.assertGreaterEqual(gates["newly_correct_vs_control_min"], 3)
        self.assertLessEqual(gates["regression_vs_control_max"], 1)
        self.assertGreaterEqual(gates["net_correct_gain_vs_control_min"], 2)
        self.assertEqual(gates["candidate_tool_parse_success_count"], 12)
        self.assertEqual(gates["candidate_index_contract_success_count"], 12)
        invariants = self.config["run_invariants"]
        self.assertEqual(invariants["model_call_count_exact"], 36)
        self.assertEqual(invariants["transport_attempt_count_exact"], 36)
        self.assertEqual(invariants["calls_per_model_exact"], 12)
        self.assertFalse(invariants["post_failure_retry_authorized"])
        self.assertFalse(invariants["interim_label_inspection_authorized"])

    def test_selection_stops_model_swapping_when_none_is_eligible(self):
        selection = self.config["selection_rule"]
        self.assertIn("two-stage", selection["no_eligible_model"])
        self.assertIn(
            "stop single-call model replacement",
            self.config["decision_rule"]["no_candidate_selected"],
        )

    def test_no_inference_runtime_or_broad_claim_is_authorized(self):
        self.assertFalse(
            self.config[
                "model_inference_before_preregistration_and_harness_merge_authorized"
            ]
        )
        for value in self.config["evidence_limits"].values():
            self.assertFalse(value)
        if RESULT_LOCK_PATH.exists():
            result_lock = _load(RESULT_LOCK_PATH)
            harness_commit = result_lock["harness_merge_commit"]
            for path in RESULT_PATHS:
                completed = subprocess.run(
                    [
                        "git",
                        "cat-file",
                        "-e",
                        f"{harness_commit}:{path.relative_to(ROOT)}",
                    ],
                    cwd=ROOT,
                    capture_output=True,
                    check=False,
                )
                self.assertNotEqual(completed.returncode, 0)
        else:
            for path in RESULT_PATHS:
                self.assertFalse(path.exists())


if __name__ == "__main__":
    unittest.main()
