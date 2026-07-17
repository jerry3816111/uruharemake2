#!/usr/bin/env python3
"""Validate support-attribution V1 preregistration and dataset."""

from __future__ import annotations

import hashlib
import json
import unittest
from collections import Counter
from pathlib import Path

from consolidation_support_attribution_v1_core import (
    build_coarse_control_rows,
    summarize_condition,
)


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = (
    ROOT
    / "configs"
    / "consolidation_support_attribution_v1_development_preregistration.json"
)
LOCK_PATH = (
    ROOT
    / "configs"
    / "consolidation_support_attribution_v1_harness_lock.json"
)


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _collect_prior_source_texts(payload):
    texts = set()
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key in {
                "user",
                "target_user_utterance",
                "local_distractor_template",
                "global_distractor_template",
            } and isinstance(value, str):
                texts.add(value)
            texts.update(_collect_prior_source_texts(value))
    elif isinstance(payload, list):
        for value in payload:
            texts.update(_collect_prior_source_texts(value))
    return texts


class ConsolidationSupportAttributionV1PreregistrationTest(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls):
        cls.config = _load(CONFIG_PATH)
        cls.lock = _load(LOCK_PATH)
        cls.dataset = _load(ROOT / cls.config["dataset"]["path"])
        cls.cases = cls.dataset["cases"]

    def test_identity_and_single_variable_are_explicit(self):
        self.assertEqual(
            self.config["experiment_id"],
            "consolidation_support_attribution_v1_development",
        )
        self.assertEqual(
            self.config["single_manipulated_variable"],
            (
                "replace_the_complete_six_event_batch_pointer_with_"
                "qwen35_4b_selected_explicit_support_event_indices"
            ),
        )
        self.assertFalse(
            self.config[
                "model_inference_before_harness_merge_authorized"
            ]
        )

    def test_dataset_is_balanced_fresh_and_unambiguous(self):
        self.assertEqual(len(self.cases), 18)
        self.assertEqual(
            Counter(case["language"] for case in self.cases),
            {"eng": 6, "jpn": 6, "cmn": 6},
        )
        self.assertEqual(
            Counter(case["memory_kind"] for case in self.cases),
            {"episodic": 6, "wisdom": 6, "procedural": 6},
        )
        self.assertEqual(
            Counter(case["support_mode"] for case in self.cases),
            {"supported": 12, "unsupported": 6},
        )
        self.assertEqual(
            len({case["scenario_family"] for case in self.cases}),
            18,
        )
        for case in self.cases:
            self.assertEqual(
                [event["index"] for event in case["source_events"]],
                list(range(1, 7)),
            )
            gold = case["gold_support_event_indices"]
            self.assertEqual(len(gold), len(set(gold)))
            self.assertTrue(all(index in range(1, 7) for index in gold))
            self.assertEqual(
                bool(gold),
                case["support_mode"] == "supported",
            )

    def test_no_exact_source_text_is_reused_from_consumed_datasets(self):
        prior_paths = (
            ROOT / "datasets" / "consolidation_source_pointer_v1.json",
            ROOT
            / "datasets"
            / "consolidation_admission_model_screen_v1_development.json",
            ROOT
            / "datasets"
            / "consolidation_admission_cascade_v1_development.json",
        )
        prior_texts = set()
        for path in prior_paths:
            prior_texts.update(_collect_prior_source_texts(_load(path)))
        current_texts = {
            event["user"]
            for case in self.cases
            for event in case["source_events"]
        }
        self.assertFalse(prior_texts & current_texts)

    def test_frozen_baseline_is_recomputed_from_current_behavior(self):
        observed = summarize_condition(
            self.cases,
            build_coarse_control_rows(self.cases),
        )
        for key, expected in self.config["frozen_baseline"].items():
            if key == "model_calls":
                self.assertEqual(expected, 0)
                continue
            self.assertEqual(observed[key], expected, key)

    def test_model_and_success_gates_are_frozen(self):
        self.assertEqual(self.config["model"]["ollama_tag"], "qwen3.5:4b")
        self.assertEqual(
            self.config["model"]["digest"],
            (
                "2a654d98e6fba55d452b7043684e9b57a947e393bbffa624"
                "85a7aac05ee4eefd"
            ),
        )
        gates = self.config["success_gates"]
        self.assertEqual(gates["candidate_exact_set_match_count_min"], 14)
        self.assertEqual(
            gates["candidate_positive_complete_support_count_min"],
            11,
        )
        self.assertEqual(
            gates["candidate_unsupported_empty_count_min"],
            5,
        )
        self.assertEqual(gates["candidate_evidence_precision_min"], 0.9)
        self.assertEqual(gates["candidate_evidence_recall_min"], 0.9)
        self.assertEqual(gates["candidate_false_source_count_max"], 2)
        self.assertEqual(
            gates["candidate_parse_success_count_exact"],
            18,
        )

    def test_gold_is_scorer_only_and_runtime_claims_are_forbidden(self):
        controlled = " ".join(self.config["controlled_variables"])
        prohibited = " ".join(self.config["prohibited_changes"])
        self.assertIn("gold source indices remain analyzer-only", controlled)
        self.assertIn("gold_support_event_indices", prohibited)
        limits = self.config["evidence_limits"]
        self.assertFalse(limits["runtime_integration_authorized"])
        self.assertFalse(limits["downstream_dialogue_improvement_claim_authorized"])
        self.assertFalse(limits["human_likeness_claim_authorized"])
        self.assertFalse(limits["biological_equivalence_claim_authorized"])

    def test_all_preregistered_artifacts_are_hash_bound(self):
        self.assertEqual(
            _sha256(ROOT / self.config["dataset"]["path"]),
            self.config["dataset"]["sha256"],
        )
        for name, expected in self.lock["frozen_artifacts"].items():
            if not name.endswith("_sha256"):
                continue
            path_key = name.removesuffix("_sha256")
            self.assertEqual(
                _sha256(ROOT / self.lock["paths"][path_key]),
                expected,
                path_key,
            )

    def test_result_artifacts_do_not_exist_before_model_run(self):
        for relative_path in self.config["result_artifacts"]:
            self.assertFalse((ROOT / relative_path).exists(), relative_path)


if __name__ == "__main__":
    unittest.main()
