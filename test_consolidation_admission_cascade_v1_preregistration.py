#!/usr/bin/env python3
"""Validate the consolidation-admission cascade V1 preregistration."""

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
    / "consolidation_admission_cascade_v1_development_preregistration.json"
)
DATASET_PATH = (
    ROOT
    / "datasets"
    / "consolidation_admission_cascade_v1_development.json"
)
MODEL_SCREEN_RESULT_LOCK_PATH = (
    ROOT
    / "configs"
    / "consolidation_admission_model_screen_v1_result_lock.json"
)
V3_CONFIG_PATH = (
    ROOT
    / "configs"
    / "consolidation_admission_v3_role_separated_development_preregistration.json"
)
RUNTIME_PATH = ROOT / "uruha_brain_mac.py"
PRIOR_DATASET_PATHS = (
    ROOT / "datasets" / "consolidation_admission_v1_development.json",
    ROOT / "datasets" / "consolidation_admission_v2_indexed_development.json",
    ROOT
    / "datasets"
    / "consolidation_admission_v3_role_separated_development.json",
    ROOT
    / "datasets"
    / "consolidation_admission_model_screen_v1_development.json",
)
RESULT_PATHS = (
    ROOT
    / "reports"
    / "consolidation_admission_cascade_v1_development_raw.json",
    ROOT
    / "reports"
    / "consolidation_admission_cascade_v1_development_analysis.json",
    ROOT
    / "reports"
    / "consolidation_admission_cascade_v1_development_analysis.md",
    ROOT
    / "reports"
    / "consolidation_admission_cascade_v1_development_diagnostic_zh.md",
    ROOT
    / "configs"
    / "consolidation_admission_cascade_v1_result_lock.json",
)
RESULT_LOCK_PATH = (
    ROOT
    / "configs"
    / "consolidation_admission_cascade_v1_result_lock.json"
)


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ConsolidationAdmissionCascadeV1PreregistrationTest(
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
            "consolidation_admission_cascade_v1_development",
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
            kind = case["expected_memory_kind"]
            basis = case["expected_persistence_basis"]
            self.assertEqual(case["expected_applies_to"], applies_to[kind])
            required = case["required_evidence_user_turns"]
            allowed = case["allowed_evidence_user_turns"]
            self.assertEqual(len(required), len(set(required)))
            self.assertEqual(len(allowed), len(set(allowed)))
            self.assertTrue(set(required) <= set(allowed))
            self.assertTrue(
                all(index in {1, 2, 3} for index in required + allowed)
            )
            if kind == "none":
                self.assertEqual(basis, "no_long_term_basis")
                self.assertEqual(required, [])
                self.assertEqual(allowed, [])
            else:
                self.assertTrue(required)
            if basis == "repeated_pattern":
                self.assertGreaterEqual(len(required), 2)
            if kind == "procedural":
                self.assertEqual(basis, "explicit_future_policy")

    def test_no_exact_utterance_or_available_scenario_family_overlap(self):
        current_utterances = {
            turn["user"].strip().casefold()
            for case in self.dataset["cases"]
            for turn in case["session"]
        }
        current_families = {
            case["scenario_family"] for case in self.dataset["cases"]
        }
        prior_utterances = set()
        prior_families = set()
        for path in PRIOR_DATASET_PATHS:
            payload = _load(path)
            prior_utterances.update(
                turn["user"].strip().casefold()
                for case in payload["cases"]
                for turn in case["session"]
            )
            prior_families.update(
                case["scenario_family"]
                for case in payload["cases"]
                if "scenario_family" in case
            )
        self.assertEqual(current_utterances & prior_utterances, set())
        self.assertEqual(current_families & prior_families, set())

    def test_model_screen_failure_is_hash_bound_and_not_retested(self):
        evidence = self.config["existing_evidence"]
        self.assertEqual(
            evidence["model_screen_result_lock_sha256"],
            _sha256(MODEL_SCREEN_RESULT_LOCK_PATH),
        )
        self.assertEqual(evidence["result"], "FAIL")
        self.assertFalse(evidence["same_dataset_retest_authorized"])
        self.assertFalse(
            evidence["exploratory_replay_validation_claim_authorized"]
        )
        prior = _load(MODEL_SCREEN_RESULT_LOCK_PATH)
        self.assertEqual(evidence["decision"], prior["decision"])
        self.assertNotEqual(
            self.config["dataset"]["sha256"],
            prior["frozen_artifacts"]["dataset_sha256"],
        )

    def test_runtime_mapping_is_hash_bound_but_not_modified(self):
        mapping = self.config["runtime_mapping"]
        self.assertEqual(mapping["sha256"], _sha256(RUNTIME_PATH))
        self.assertEqual(
            mapping["entry_point"],
            "MemoryManager.consolidate_recent_experiences",
        )
        self.assertIn("admission adapter", mapping["candidate_mapping"])
        self.assertIn("Chroma shadow writes", mapping["not_tested_here"])

    def test_final_classifier_is_exact_frozen_v3_candidate(self):
        source = self.v3_config["conditions"][
            "v3_role_separated_tool_candidate"
        ]
        final = self.config["final_classifier"]
        self.assertEqual(final["system_prompt"], source["system_prompt"])
        self.assertEqual(final["tool_contract"], source["tool_contract"])
        self.assertEqual(
            final["deterministic_compiler"],
            source["deterministic_compiler"],
        )

    def test_stage1_contract_is_binary_and_does_not_leak_final_labels(self):
        stage1 = self.config["stage1_write_gate"]
        parameters = stage1["tool_contract"]["function"]["parameters"]
        self.assertFalse(parameters["additionalProperties"])
        self.assertEqual(parameters["required"], ["admission_decision"])
        self.assertEqual(
            parameters["properties"]["admission_decision"]["enum"],
            ["write", "none"],
        )
        serialized = json.dumps(stage1, ensure_ascii=False)
        for forbidden in (
            "memory_kind",
            "persistence_basis",
            "evidence_user_turns",
            "user_profile",
            "assistant_policy",
        ):
            self.assertNotIn(forbidden, serialized)

    def test_prompts_contain_no_case_text_or_gold_fields(self):
        serialized = json.dumps(
            {
                "stage1": self.config["stage1_write_gate"],
                "final": self.config["final_classifier"],
            },
            ensure_ascii=False,
        )
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

    def test_matched_control_and_cascade_change_only_the_write_gate(self):
        conditions = self.config["conditions"]
        self.assertEqual(
            set(conditions),
            {
                "direct_qwen35_9b_control",
                "qwen35_4b_to_9b_cascade",
            },
        )
        self.assertEqual(
            conditions["direct_qwen35_9b_control"]["calls_exact"], 12
        )
        candidate = conditions["qwen35_4b_to_9b_cascade"]
        self.assertEqual(candidate["stage1_calls_exact"], 12)
        self.assertEqual(
            candidate["stage2_calls_equal"],
            "compiled_stage1_write_count",
        )
        self.assertEqual(
            candidate["only_changed_component_vs_control"],
            "add_a_conditional_qwen35_4b_write_gate_before_the_same_qwen35_9b_final_classifier",
        )

    def test_success_requires_accuracy_safety_pairwise_gain_and_cost(self):
        gates = self.config["success_gates"]
        self.assertGreaterEqual(gates["candidate_correct_count_min"], 11)
        self.assertEqual(gates["candidate_none_correct_exact"], 4)
        self.assertEqual(gates["stage1_positive_write_count_exact"], 8)
        self.assertEqual(
            gates["candidate_false_long_term_write_count_exact"], 0
        )
        self.assertLessEqual(
            gates["candidate_missed_long_term_write_count_max"], 1
        )
        self.assertGreaterEqual(gates["net_correct_gain_vs_control_min"], 1)
        self.assertEqual(gates["regression_vs_control_max"], 0)
        self.assertLessEqual(gates["stage2_call_count_max"], 10)
        self.assertLessEqual(
            gates["candidate_mean_session_wall_seconds_max"], 8.5
        )
        invariants = self.config["run_invariants"]
        self.assertEqual(invariants["control_calls_exact"], 12)
        self.assertEqual(invariants["stage1_calls_exact"], 12)
        self.assertEqual(invariants["total_model_calls_max"], 34)
        self.assertFalse(invariants["transport_retries_authorized"])
        self.assertFalse(invariants["interim_label_inspection_authorized"])

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
