#!/usr/bin/env python3
"""Validate the frozen support-attribution runtime pilot design."""

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
    / "consolidation_support_runtime_v1_preregistration.json"
)
BASELINE_COMMIT = "bff1d4c81c7abfce568d4c2e20dc58c996972458"
MEMORY_KINDS = ("episodic", "wisdom", "procedural")


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_file_exists(commit, path):
    completed = subprocess.run(
        ["git", "cat-file", "-e", f"{commit}:{path}"],
        cwd=ROOT,
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return completed.returncode == 0


def _collect_user_texts(payload):
    texts = set()
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key == "user" and isinstance(value, str):
                texts.add(value)
            texts.update(_collect_user_texts(value))
    elif isinstance(payload, list):
        for value in payload:
            texts.update(_collect_user_texts(value))
    return texts


class ConsolidationSupportRuntimeV1PreregistrationTest(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls):
        cls.config = _load(CONFIG_PATH)
        cls.dataset_path = ROOT / cls.config["dataset"]["path"]
        cls.dataset = _load(cls.dataset_path)
        cls.cases = cls.dataset["cases"]

    def test_identity_single_variable_and_execution_boundaries(self):
        self.assertEqual(
            self.config["experiment_id"],
            "consolidation_support_runtime_v1_pilot",
        )
        self.assertEqual(
            self.config["single_manipulated_variable"],
            (
                "optional_per_derived_memory_support_attribution_"
                "between_frozen_payload_generation_and_chroma_persistence"
            ),
        )
        self.assertFalse(
            self.config[
                "runtime_change_before_preregistration_merge_authorized"
            ]
        )
        self.assertFalse(
            self.config[
                "formal_model_inference_before_harness_merge_authorized"
            ]
        )

    def test_dataset_is_fresh_balanced_and_structurally_complete(self):
        self.assertEqual(len(self.cases), 6)
        self.assertEqual(
            Counter(case["language"] for case in self.cases),
            {"eng": 2, "jpn": 2, "cmn": 2},
        )
        self.assertEqual(
            len({case["scenario_family"] for case in self.cases}),
            6,
        )
        unsupported = Counter()
        stored_count = 0
        for case in self.cases:
            self.assertEqual(
                [event["index"] for event in case["source_events"]],
                list(range(1, 7)),
            )
            self.assertEqual(
                set(case["generated_payload"]),
                {
                    "episodic_summary",
                    "wisdom_rule",
                    "procedural_rule",
                    "salience",
                },
            )
            gold = case["gold_support_event_indices"]
            self.assertEqual(set(gold), set(MEMORY_KINDS))
            for kind in MEMORY_KINDS:
                indices = gold[kind]
                self.assertEqual(len(indices), len(set(indices)))
                self.assertTrue(
                    all(index in range(1, 7) for index in indices)
                )
                if not indices:
                    unsupported[kind] += 1
            outcome = case["expected_candidate_outcome"]
            stored_count += len(outcome["stored_memory_kinds"])
            if not gold["episodic"]:
                self.assertEqual(
                    outcome["batch_status"],
                    "rejected_unsupported_episodic",
                )
                self.assertEqual(outcome["stored_memory_kinds"], [])
            else:
                self.assertEqual(outcome["batch_status"], "stored")
                self.assertEqual(
                    set(outcome["stored_memory_kinds"]),
                    {
                        kind
                        for kind in MEMORY_KINDS
                        if gold[kind]
                    },
                )
        self.assertEqual(
            unsupported,
            {"episodic": 1, "wisdom": 1, "procedural": 1},
        )
        self.assertEqual(stored_count, 13)

    def test_no_exact_user_text_is_reused_from_consumed_datasets(self):
        prior_paths = (
            ROOT
            / "datasets"
            / "consolidation_support_attribution_v1_development.json",
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
            prior_texts.update(_collect_user_texts(_load(path)))
        current_texts = {
            event["user"]
            for case in self.cases
            for event in case["source_events"]
        }
        self.assertFalse(prior_texts & current_texts)

    def test_dataset_and_current_runtime_baseline_are_hash_bound(self):
        self.assertEqual(
            _sha256(self.dataset_path),
            self.config["dataset"]["sha256"],
        )
        frozen = self.config["frozen_runtime_baseline"]
        runtime = subprocess.check_output(
            ["git", "show", f"{frozen['commit']}:{frozen['path']}"],
            cwd=ROOT,
        )
        self.assertEqual(
            hashlib.sha256(runtime).hexdigest(),
            frozen["sha256"],
        )

    def test_coarse_runtime_baseline_is_recomputed_from_dataset(self):
        true_positive = 0
        false_positive = 0
        false_negative = 0
        exact = 0
        unsupported_written = 0
        for case in self.cases:
            for kind in MEMORY_KINDS:
                expected = set(
                    case["gold_support_event_indices"][kind]
                )
                predicted = set(range(1, 7))
                true_positive += len(expected & predicted)
                false_positive += len(predicted - expected)
                false_negative += len(expected - predicted)
                exact += predicted == expected
                unsupported_written += not expected
        baseline = self.config["frozen_runtime_baseline"]
        self.assertEqual(baseline["derived_record_count"], 18)
        self.assertEqual(
            baseline["derived_records_with_exact_support_set"],
            exact,
        )
        self.assertEqual(
            baseline["unsupported_derived_records_written"],
            unsupported_written,
        )
        self.assertEqual(
            baseline["true_support_source_count"],
            true_positive,
        )
        self.assertEqual(
            baseline["false_support_source_count"],
            false_positive,
        )
        self.assertEqual(false_negative, 0)
        self.assertEqual(
            baseline["evidence_precision"],
            round(
                true_positive / (true_positive + false_positive),
                4,
            ),
        )
        self.assertEqual(baseline["evidence_recall"], 1.0)

    def test_prior_result_authorizes_only_this_fresh_pilot(self):
        prior = self.config["prior_evidence"][
            "support_attribution_result"
        ]
        self.assertEqual(_sha256(ROOT / prior["path"]), prior["sha256"])
        result = _load(ROOT / prior["path"])
        self.assertEqual(result["decision"], prior["decision"])
        self.assertTrue(result["results"]["all_success_gates_passed"])
        self.assertFalse(result["runtime_integration_authorized"])
        self.assertIn(
            "fresh temporary-Chroma runtime integration pilot",
            result["next_primary_task"],
        )

    def test_atomicity_model_and_runtime_gates_cannot_be_bypassed(self):
        semantics = self.config["candidate_runtime_semantics"]
        self.assertIn("Store nothing", semantics["unsupported_episodic"])
        self.assertIn(
            "Delete every candidate derived record",
            semantics["derived_write_failure"],
        )
        self.assertIn(
            "Restore source metadata",
            semantics["source_transition_failure"],
        )
        gates = self.config["success_gates"]
        self.assertEqual(
            gates["candidate_exact_support_set_count_min"],
            16,
        )
        self.assertEqual(
            gates["candidate_stored_record_count_exact"],
            13,
        )
        self.assertEqual(
            gates[
                "candidate_stored_records_with_exact_support_metadata_exact"
            ],
            13,
        )
        self.assertEqual(
            gates["candidate_unsupported_derived_records_written_exact"],
            0,
        )
        self.assertEqual(
            gates["candidate_partial_batch_count_exact"],
            0,
        )
        self.assertTrue(
            gates["injected_each_collection_write_failure_is_atomic"]
        )
        self.assertTrue(
            gates["injected_source_transition_failure_is_atomic"]
        )

    def test_gold_production_and_claim_boundaries_are_explicit(self):
        controlled = " ".join(self.config["controlled_variables"])
        prohibited = " ".join(self.config["prohibited_changes"])
        self.assertIn("gold source indices remain analyzer-only", controlled)
        self.assertIn("gold_support_event_indices", prohibited)
        self.assertIn("production Chroma", prohibited)
        limits = self.config["evidence_limits"]
        for key in (
            "production_activation_authorized",
            "production_data_migration_authorized",
            "retrieval_improvement_claim_authorized",
            "downstream_dialogue_improvement_claim_authorized",
            "human_likeness_claim_authorized",
            "biological_equivalence_claim_authorized",
        ):
            self.assertFalse(limits[key], key)

    def test_result_artifacts_are_absent_at_frozen_baseline(self):
        for relative_path in self.config["result_artifacts"]:
            self.assertFalse(
                _git_file_exists(BASELINE_COMMIT, relative_path),
                relative_path,
            )


if __name__ == "__main__":
    unittest.main()
