#!/usr/bin/env python3
"""Validate V2 indexed consolidation preregistration without inference."""

from __future__ import annotations

import hashlib
import json
import unittest
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = (
    ROOT
    / "configs"
    / "consolidation_admission_v2_indexed_development_preregistration.json"
)
DATASET_PATH = (
    ROOT / "datasets" / "consolidation_admission_v2_indexed_development.json"
)
V1_CONFIG_PATH = (
    ROOT / "configs" / "consolidation_admission_v1_development_preregistration.json"
)
V1_DATASET_PATH = (
    ROOT / "datasets" / "consolidation_admission_v1_development.json"
)
V1_RESULT_LOCK_PATH = (
    ROOT / "configs" / "consolidation_admission_v1_result_lock.json"
)
RESULT_PATHS = (
    ROOT / "reports" / "consolidation_admission_v2_indexed_development_raw.json",
    ROOT
    / "reports"
    / "consolidation_admission_v2_indexed_development_analysis.json",
    ROOT
    / "reports"
    / "consolidation_admission_v2_indexed_development_analysis.md",
    ROOT / "configs" / "consolidation_admission_v2_indexed_result_lock.json",
)


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ConsolidationAdmissionV2PreregistrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = _load(CONFIG_PATH)
        cls.dataset = _load(DATASET_PATH)

    def test_experiment_identity_and_dataset_hash_are_stable(self):
        self.assertEqual(
            self.config["experiment_id"],
            "consolidation_admission_v2_indexed_development",
        )
        self.assertEqual(
            self.config["dataset"]["sha256"], _sha256(DATASET_PATH)
        )
        self.assertEqual(len(self.dataset["cases"]), 18)

    def test_dataset_is_balanced_unique_and_not_translated(self):
        cases = self.dataset["cases"]
        self.assertEqual(
            Counter(case["language"] for case in cases),
            Counter({"eng": 6, "jpn": 6, "cmn": 6}),
        )
        self.assertEqual(
            Counter(case["expected_memory_kind"] for case in cases),
            Counter({"wisdom": 6, "procedural": 6, "none": 6}),
        )
        self.assertEqual(len({case["id"] for case in cases}), 18)
        self.assertEqual(
            len({case["scenario_family"] for case in cases}), 18
        )
        self.assertFalse(self.dataset["semantic_translation_pairs_present"])
        self.assertFalse(self.dataset["official_source_labels"])
        self.assertFalse(self.dataset["independent_human_label_validation"])
        self.assertFalse(
            self.dataset["model_inference_used_during_construction"]
        )

    def test_gold_frames_and_evidence_indices_are_structurally_valid(self):
        for case in self.dataset["cases"]:
            self.assertEqual(len(case["session"]), 3)
            required = case["required_evidence_user_turns"]
            allowed = case["allowed_evidence_user_turns"]
            self.assertEqual(len(required), len(set(required)))
            self.assertEqual(len(allowed), len(set(allowed)))
            self.assertTrue(
                all(index in {1, 2, 3} for index in required + allowed)
            )
            self.assertTrue(set(required) <= set(allowed))
            if case["expected_memory_kind"] == "none":
                self.assertEqual(required, [])
                self.assertEqual(allowed, [])
            else:
                self.assertTrue(required)
                self.assertTrue(allowed)
            if case["expected_scope"] == "repeated":
                self.assertGreaterEqual(len(required), 2)
            if case["expected_memory_kind"] == "procedural":
                self.assertEqual(case["expected_scope"], "recurring")
                self.assertEqual(case["expected_owner"], "assistant")

    def test_no_exact_user_utterance_overlap_with_v1(self):
        v1 = _load(V1_DATASET_PATH)
        current_texts = {
            turn["user"].strip().casefold()
            for case in self.dataset["cases"]
            for turn in case["session"]
        }
        v1_texts = {
            turn["user"].strip().casefold()
            for case in v1["cases"]
            for turn in case["session"]
        }
        self.assertEqual(current_texts & v1_texts, set())

    def test_v1_failure_is_hash_bound_and_not_retested(self):
        dependency = self.config["v1_dependency"]
        self.assertEqual(
            dependency["result_lock_sha256"], _sha256(V1_RESULT_LOCK_PATH)
        )
        self.assertEqual(dependency["result"], "FAIL")
        self.assertFalse(dependency["same_dataset_retest_authorized"])
        self.assertNotEqual(
            self.config["dataset"]["sha256"],
            _load(V1_CONFIG_PATH)["dataset"]["sha256"],
        )

    def test_control_is_exactly_the_frozen_v1_candidate_contract(self):
        v1 = _load(V1_CONFIG_PATH)
        control = self.config["conditions"]["v1_source_bound_json_control"]
        self.assertEqual(
            control["system_prompt"],
            v1["conditions"]["source_bound_layered_candidate"][
                "system_prompt"
            ],
        )
        self.assertEqual(
            self.config["generation"]["maximum_output_tokens"],
            v1["generation"]["maximum_output_tokens"],
        )

    def test_candidate_tool_contract_is_small_and_closed(self):
        candidate = self.config["conditions"]["v2_indexed_tool_candidate"]
        function = candidate["tool_contract"]["function"]
        parameters = function["parameters"]
        self.assertEqual(function["name"], "classify_memory_admission")
        self.assertFalse(parameters["additionalProperties"])
        self.assertEqual(
            set(parameters["required"]),
            {
                "memory_kind",
                "scope",
                "owner",
                "evidence_user_turns",
                "confidence_band",
            },
        )
        self.assertEqual(
            parameters["properties"]["evidence_user_turns"]["items"]["enum"],
            [1, 2, 3],
        )
        self.assertEqual(
            parameters["properties"]["confidence_band"]["enum"],
            ["low", "medium", "high"],
        )

    def test_candidate_prompt_contains_no_case_text_or_gold(self):
        candidate = self.config["conditions"]["v2_indexed_tool_candidate"]
        serialized = json.dumps(candidate, ensure_ascii=False)
        for case in self.dataset["cases"]:
            self.assertNotIn(case["id"], serialized)
            self.assertNotIn(case["session"][0]["user"], serialized)
            self.assertNotIn(case["gold_reason"], serialized)
        for forbidden in (
            "expected_memory_kind",
            "expected_scope",
            "expected_owner",
            "required_evidence_user_turns",
            "allowed_evidence_user_turns",
        ):
            self.assertNotIn(forbidden, serialized)

    def test_only_output_decomposition_changes_between_conditions(self):
        conditions = self.config["conditions"]
        self.assertEqual(
            set(conditions),
            {"v1_source_bound_json_control", "v2_indexed_tool_candidate"},
        )
        self.assertEqual(
            conditions["v1_source_bound_json_control"]["model_calls"],
            conditions["v2_indexed_tool_candidate"]["model_calls"],
        )
        self.assertEqual(
            conditions["v2_indexed_tool_candidate"][
                "only_changed_component"
            ],
            "source_index_transport_and_admission_output_decomposition",
        )
        self.assertEqual(self.config["model"]["name"], "qwen2.5:7b")
        self.assertEqual(self.config["generation"]["temperature"], 0.1)
        self.assertEqual(self.config["generation"]["seed"], 20260717)

    def test_transcript_uses_real_line_breaks_and_explicit_roles(self):
        rendering = self.config["fixed_transcript_rendering"]
        self.assertEqual(rendering.count("\n"), 2)
        self.assertNotIn("\\n", rendering)
        self.assertIn("User[U{index}]", rendering)
        self.assertIn("Assistant[A{index}]", rendering)

    def test_success_requires_target_frame_evidence_gain_and_latency(self):
        gates = self.config["success_gates"]
        self.assertGreaterEqual(gates["candidate_correct_count_min"], 16)
        for target in ("wisdom", "procedural", "none"):
            self.assertGreaterEqual(
                gates[f"candidate_{target}_correct_min"], 5
            )
        self.assertGreaterEqual(gates["candidate_frame_exact_count_min"], 15)
        self.assertGreaterEqual(
            gates["candidate_evidence_grounded_count_min"], 15
        )
        self.assertGreaterEqual(
            gates["candidate_positive_evidence_grounded_count_min"], 10
        )
        self.assertGreaterEqual(gates["newly_correct_vs_control_min"], 5)
        self.assertLessEqual(gates["regression_vs_control_max"], 1)
        self.assertGreaterEqual(
            gates["net_correct_gain_vs_control_min"], 4
        )
        self.assertLessEqual(
            gates["candidate_false_long_term_write_count_max"], 1
        )
        self.assertLessEqual(
            gates["candidate_missed_long_term_write_count_max"], 1
        )
        self.assertEqual(gates["model_call_count_exact"], 36)

    def test_no_inference_runtime_or_broad_claim_is_authorized(self):
        self.assertFalse(
            self.config[
                "model_inference_before_preregistration_and_harness_merge_authorized"
            ]
        )
        for value in self.config["evidence_limits"].values():
            self.assertFalse(value)
        for path in RESULT_PATHS:
            self.assertFalse(path.exists())


if __name__ == "__main__":
    unittest.main()
