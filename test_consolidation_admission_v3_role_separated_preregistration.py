#!/usr/bin/env python3
"""Validate V3 role-separated consolidation preregistration."""

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
    / "consolidation_admission_v3_role_separated_development_preregistration.json"
)
DATASET_PATH = (
    ROOT
    / "datasets"
    / "consolidation_admission_v3_role_separated_development.json"
)
V2_CONFIG_PATH = (
    ROOT
    / "configs"
    / "consolidation_admission_v2_indexed_development_preregistration.json"
)
V2_RESULT_LOCK_PATH = (
    ROOT / "configs" / "consolidation_admission_v2_indexed_result_lock.json"
)
PRIOR_DATASET_PATHS = (
    ROOT / "datasets" / "consolidation_admission_v1_development.json",
    ROOT / "datasets" / "consolidation_admission_v2_indexed_development.json",
)
RESULT_PATHS = (
    ROOT
    / "reports"
    / "consolidation_admission_v3_role_separated_development_raw.json",
    ROOT
    / "reports"
    / "consolidation_admission_v3_role_separated_development_analysis.json",
    ROOT
    / "reports"
    / "consolidation_admission_v3_role_separated_development_analysis.md",
    ROOT
    / "configs"
    / "consolidation_admission_v3_role_separated_result_lock.json",
)
RESULT_LOCK_PATH = (
    ROOT
    / "configs"
    / "consolidation_admission_v3_role_separated_result_lock.json"
)


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ConsolidationAdmissionV3PreregistrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = _load(CONFIG_PATH)
        cls.dataset = _load(DATASET_PATH)

    def test_experiment_identity_and_dataset_hash_are_stable(self):
        self.assertEqual(
            self.config["experiment_id"],
            "consolidation_admission_v3_role_separated_development",
        )
        self.assertEqual(self.config["dataset"]["sha256"], _sha256(DATASET_PATH))
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
        self.assertEqual(
            Counter(case["expected_persistence_basis"] for case in cases),
            Counter(
                {
                    "stable_trait": 3,
                    "repeated_pattern": 3,
                    "explicit_future_policy": 6,
                    "no_long_term_basis": 6,
                }
            ),
        )
        self.assertEqual(len({case["id"] for case in cases}), 18)
        self.assertEqual(len({case["scenario_family"] for case in cases}), 18)
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

    def test_no_exact_user_utterance_overlap_with_v1_or_v2(self):
        current = {
            turn["user"].strip().casefold()
            for case in self.dataset["cases"]
            for turn in case["session"]
        }
        prior = set()
        for path in PRIOR_DATASET_PATHS:
            payload = _load(path)
            prior.update(
                turn["user"].strip().casefold()
                for case in payload["cases"]
                for turn in case["session"]
            )
        self.assertEqual(current & prior, set())

    def test_v2_failure_is_hash_bound_and_not_retested(self):
        dependency = self.config["v2_dependency"]
        self.assertEqual(
            dependency["result_lock_sha256"], _sha256(V2_RESULT_LOCK_PATH)
        )
        self.assertEqual(dependency["result"], "FAIL")
        self.assertFalse(dependency["same_dataset_retest_authorized"])
        self.assertNotEqual(
            self.config["dataset"]["sha256"],
            _load(V2_CONFIG_PATH)["dataset"]["sha256"],
        )

    def test_control_is_exact_frozen_v2_candidate(self):
        v2 = _load(V2_CONFIG_PATH)
        source = v2["conditions"]["v2_indexed_tool_candidate"]
        control = self.config["conditions"]["v2_indexed_tool_control"]
        self.assertEqual(control["system_prompt"], source["system_prompt"])
        self.assertEqual(control["tool_contract"], source["tool_contract"])
        self.assertEqual(self.config["generation"], v2["generation"])
        self.assertEqual(self.config["model"], v2["model"])

    def test_candidate_tool_contract_contains_only_semantic_decisions(self):
        candidate = self.config["conditions"][
            "v3_role_separated_tool_candidate"
        ]
        parameters = candidate["tool_contract"]["function"]["parameters"]
        self.assertFalse(parameters["additionalProperties"])
        self.assertEqual(
            set(parameters["required"]),
            {
                "memory_kind",
                "persistence_basis",
                "evidence_user_turns",
            },
        )
        serialized = json.dumps(parameters, ensure_ascii=False)
        for forbidden in ("owner", "target", "source_role", "confidence"):
            self.assertNotIn(forbidden, serialized)

    def test_candidate_compiler_preserves_source_and_derives_applicability(self):
        compiler = self.config["conditions"][
            "v3_role_separated_tool_candidate"
        ]["deterministic_compiler"]
        self.assertIn("User turn", compiler["source_role"])
        self.assertIn("applies_to=user_profile", compiler["wisdom"])
        self.assertIn("applies_to=assistant_policy", compiler["procedural"])
        self.assertIn("applies_to=none", compiler["none"])
        self.assertIn("compile to none", compiler["fail_closed"])

    def test_candidate_prompt_contains_no_case_text_or_gold(self):
        candidate = self.config["conditions"][
            "v3_role_separated_tool_candidate"
        ]
        serialized = json.dumps(candidate, ensure_ascii=False)
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

    def test_only_role_separation_changes_between_conditions(self):
        conditions = self.config["conditions"]
        self.assertEqual(
            set(conditions),
            {"v2_indexed_tool_control", "v3_role_separated_tool_candidate"},
        )
        self.assertEqual(
            conditions["v2_indexed_tool_control"]["model_calls"],
            conditions["v3_role_separated_tool_candidate"]["model_calls"],
        )
        self.assertEqual(
            conditions["v3_role_separated_tool_candidate"][
                "only_changed_component"
            ],
            "separate_structural_source_and_derived_applicability_from_model_semantic_decision",
        )

    def test_success_requires_target_frame_evidence_gain_and_latency(self):
        gates = self.config["success_gates"]
        self.assertGreaterEqual(gates["candidate_correct_count_min"], 16)
        for target in ("wisdom", "procedural", "none"):
            self.assertGreaterEqual(
                gates[f"candidate_{target}_correct_min"], 5
            )
        self.assertGreaterEqual(
            gates["candidate_semantic_frame_exact_count_min"], 15
        )
        self.assertGreaterEqual(
            gates["candidate_positive_evidence_grounded_count_min"], 10
        )
        self.assertGreaterEqual(gates["newly_correct_vs_control_min"], 5)
        self.assertLessEqual(gates["regression_vs_control_max"], 1)
        self.assertGreaterEqual(gates["net_correct_gain_vs_control_min"], 4)
        self.assertEqual(gates["model_call_count_exact"], 36)

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
