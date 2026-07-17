#!/usr/bin/env python3
"""Verify the frozen negative V6 reflection-admission result."""

from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

from analyze_reflection_admission_v6_evidence_gate_development import analyze


ROOT = Path(__file__).resolve().parent
LOCK_PATH = (
    ROOT / "configs" / "reflection_admission_v6_evidence_gate_result_lock.json"
)


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ReflectionAdmissionResultTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lock = _load(LOCK_PATH)
        cls.analysis = _load(
            ROOT / cls.lock["frozen_artifacts"]["analysis_json"]
        )
        cls.raw = _load(ROOT / cls.lock["frozen_artifacts"]["raw_result"])
        cls.config = _load(
            ROOT / cls.lock["frozen_artifacts"]["preregistration"]
        )
        cls.dataset = _load(ROOT / cls.lock["frozen_artifacts"]["dataset"])

    def test_result_artifact_hashes_are_frozen(self):
        for name in (
            "preregistration",
            "harness_lock",
            "construction_closure",
            "dataset",
            "raw_result",
            "analysis_json",
            "analysis_md",
        ):
            path = ROOT / self.lock["frozen_artifacts"][name]
            self.assertEqual(
                _sha256(path),
                self.lock["frozen_artifacts"][f"{name}_sha256"],
            )

    def test_independent_analyzer_exactly_reproduces_saved_result(self):
        regenerated = analyze(
            ROOT / self.lock["frozen_artifacts"]["raw_result"]
        )
        regenerated.pop("generated_at")
        saved = dict(self.analysis)
        saved.pop("generated_at")
        self.assertEqual(regenerated, saved)

    def test_candidate_is_conservative_but_fails_positive_recall(self):
        result = self.analysis["matched_result"]
        self.assertEqual(result["control_correct_count"], 16)
        self.assertEqual(result["candidate_correct_count"], 19)
        self.assertEqual(result["candidate_accuracy"], 0.5938)
        self.assertEqual(
            self.lock["matched_result"]["delta_display"],
            "+9.38 percentage points",
        )
        self.assertEqual(result["class_metrics"]["admit"]["correct"], 3)
        self.assertEqual(result["class_metrics"]["reject"]["correct"], 16)
        self.assertEqual(result["false_admit_count"], 0)
        self.assertEqual(result["false_reject_count"], 13)
        self.assertFalse(result["all_gates_pass"])

    def test_transport_provenance_and_latency_are_complete(self):
        self.assertEqual(self.raw["model_calls"], 32)
        self.assertEqual(len(self.raw["candidate_rows"]), 32)
        self.assertTrue(
            all(
                row["transport_attempts"] == 1
                for row in self.raw["candidate_rows"]
            )
        )
        self.assertTrue(
            all(row["parse_success"] for row in self.raw["candidate_rows"])
        )
        self.assertTrue(
            all(
                row["evidence_contract_success"]
                for row in self.raw["candidate_rows"]
            )
        )
        self.assertFalse(self.raw["gold_label_passed_to_model"])
        self.assertFalse(self.raw["runtime_memory_write_performed"])

    def test_frozen_protocol_contains_the_documented_target_conflict(self):
        prompt = self.config["system_prompt"]
        self.assertIn("ordinary one-time request", prompt)
        admits = {
            case["text"]
            for case in self.dataset["cases"]
            if case["expected_admission"] == "admit"
        }
        self.assertIn("Bring Tom next time.", admits)
        self.assertIn("Next time phone ahead.", admits)
        self.assertIn(
            "Durable memory value and future-directed dialogue act",
            self.lock["causal_readout"]["protocol_definition_conflict"],
        )

    def test_failure_decision_forbids_retest_or_runtime_advancement(self):
        self.assertEqual(
            self.analysis["decision"],
            "freeze_negative_result_and_abandon_exact_evidence_gate_contract",
        )
        for name in (
            "same_dataset_retest_authorized",
            "full_pipeline_development_integration_authorized",
            "fresh_holdout_authorized",
            "runtime_memory_write_authorized",
            "runtime_shadow_authorized",
            "official_benchmark_claim_authorized",
            "cross_corpus_generalization_claim_authorized",
            "broad_human_likeness_claim_authorized",
            "downstream_dialogue_improvement_claim_authorized",
        ):
            self.assertFalse(self.lock[name])


if __name__ == "__main__":
    unittest.main()
