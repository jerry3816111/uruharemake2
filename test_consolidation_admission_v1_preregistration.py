#!/usr/bin/env python3
"""Validate V1 layered consolidation preregistration without inference."""

from __future__ import annotations

import hashlib
import json
import subprocess
import unittest
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = (
    ROOT / "configs" / "consolidation_admission_v1_development_preregistration.json"
)
DATASET_PATH = ROOT / "datasets" / "consolidation_admission_v1_development.json"
PRIOR_DATASETS = (
    ROOT / "datasets" / "reflection_admission_v6_nearmiss_development.json",
    ROOT / "datasets" / "typed_reflection_v4_development_pilot.json",
    ROOT / "datasets" / "typed_reflection_v3_development_pilot.json",
)
RESULT_PATHS = (
    ROOT / "reports" / "consolidation_admission_v1_development_raw.json",
    ROOT / "reports" / "consolidation_admission_v1_development_analysis.json",
    ROOT / "reports" / "consolidation_admission_v1_development_analysis.md",
    ROOT / "configs" / "consolidation_admission_v1_result_lock.json",
)
RESULT_LOCK_PATH = (
    ROOT / "configs" / "consolidation_admission_v1_result_lock.json"
)


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ConsolidationAdmissionPreregistrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = _load(CONFIG_PATH)
        cls.dataset = _load(DATASET_PATH)

    def test_experiment_identity_is_stable(self):
        self.assertEqual(
            self.config["schema"],
            "uruha_consolidation_admission_development_preregistration_v1",
        )
        self.assertEqual(
            self.config["experiment_id"],
            "consolidation_admission_v1_development",
        )

    def test_dataset_is_hash_bound_balanced_and_new(self):
        frozen = self.config["dataset"]
        self.assertEqual(_sha256(DATASET_PATH), frozen["sha256"])
        self.assertEqual(len(self.dataset["cases"]), 18)
        self.assertEqual(
            Counter(case["language"] for case in self.dataset["cases"]),
            Counter({"eng": 6, "jpn": 6, "cmn": 6}),
        )
        self.assertEqual(
            Counter(
                case["expected_long_term_target"]
                for case in self.dataset["cases"]
            ),
            Counter({"wisdom": 6, "procedural": 6, "none": 6}),
        )
        self.assertFalse(self.dataset["official_source_labels"])
        self.assertFalse(self.dataset["independent_human_label_validation"])
        self.assertFalse(self.dataset["model_inference_used_during_construction"])

    def test_gold_evidence_is_exact_and_ids_are_unique(self):
        ids = [case["id"] for case in self.dataset["cases"]]
        self.assertEqual(len(ids), len(set(ids)))
        for case in self.dataset["cases"]:
            user_turns = [turn["user"] for turn in case["session"]]
            self.assertEqual(len(user_turns), 3)
            for quote in case["expected_evidence_quotes"]:
                self.assertIn(quote, user_turns)
            if case["expected_long_term_target"] == "none":
                self.assertEqual(case["expected_evidence_quotes"], [])
            else:
                self.assertTrue(case["expected_evidence_quotes"])

    def test_no_exact_utterance_overlap_with_prior_reflection_data(self):
        new_texts = {
            turn["user"].strip().casefold()
            for case in self.dataset["cases"]
            for turn in case["session"]
        }
        prior_texts = set()
        for path in PRIOR_DATASETS:
            payload = _load(path)
            for case in payload.get("cases", []):
                for key in ("text", "seed_user", "followup_user"):
                    if case.get(key):
                        prior_texts.add(str(case[key]).strip().casefold())
        self.assertEqual(new_texts & prior_texts, set())

    def test_control_prompt_is_the_enabled_runtime_contract(self):
        source = (ROOT / "uruha_brain_mac.py").read_text(encoding="utf-8")
        control = self.config["conditions"]["current_direct_rule_control"]
        for sentence in (
            "You are consolidating short-term dialogue into three memory speeds.",
            "wisdom_rule is one durable semantic user fact or interaction regularity.",
            "procedural_rule is one reusable response policy in Japanese",
        ):
            self.assertIn(sentence, control["system_prompt"])
            self.assertIn(sentence, source)

    def test_only_candidate_representation_and_compiler_change(self):
        conditions = self.config["conditions"]
        self.assertEqual(set(conditions), {
            "current_direct_rule_control",
            "source_bound_layered_candidate",
        })
        self.assertEqual(
            conditions["current_direct_rule_control"]["model_calls"],
            conditions["source_bound_layered_candidate"]["model_calls"],
        )
        self.assertEqual(
            conditions["source_bound_layered_candidate"]["only_changed_component"],
            "output_representation_and_deterministic_long_term_admission",
        )
        self.assertEqual(self.config["model"]["name"], "qwen2.5:7b")
        self.assertEqual(self.config["generation"]["temperature"], 0.1)
        self.assertEqual(self.config["generation"]["seed"], 20260717)

    def test_fixed_transcript_rendering_uses_real_line_breaks(self):
        rendering = self.config["fixed_transcript_rendering"]
        self.assertEqual(rendering.count("\n"), 2)
        self.assertNotIn("\\n", rendering)

    def test_candidate_prompt_contains_no_case_text_or_gold(self):
        prompt = self.config["conditions"]["source_bound_layered_candidate"][
            "system_prompt"
        ]
        for case in self.dataset["cases"]:
            self.assertNotIn(case["id"], prompt)
            self.assertNotIn(case["session"][0]["user"], prompt)
            self.assertNotIn(case["gold_reason"], prompt)
        self.assertNotIn("expected_long_term_target", prompt)
        self.assertNotIn("expected_evidence_quotes", prompt)

    def test_success_requires_sensitivity_specificity_gain_and_latency(self):
        gates = self.config["success_gates"]
        self.assertGreaterEqual(gates["candidate_correct_count_min"], 16)
        for label in ("wisdom", "procedural", "none"):
            self.assertGreaterEqual(
                gates[f"candidate_{label}_correct_min"], 5
            )
        self.assertGreaterEqual(gates["newly_correct_vs_control_min"], 3)
        self.assertLessEqual(gates["regression_vs_control_max"], 1)
        self.assertGreaterEqual(gates["net_correct_gain_vs_control_min"], 2)
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
