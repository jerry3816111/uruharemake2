#!/usr/bin/env python3
"""Validate the frozen V5 discourse-frame development pilot contract."""

from __future__ import annotations

import hashlib
import json
import unittest
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "configs" / "reflection_hybrid_classifier_v5_discourse_frame_development_preregistration.json"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ReflectionDiscourseFramePreregistrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = _load(CONFIG)
        cls.dataset_path = ROOT / cls.config["dataset"]["path"]
        cls.dataset = _load(cls.dataset_path)

    def test_retired_development_dataset_is_frozen_and_balanced(self):
        frozen = self.config["dataset"]
        self.assertEqual(_sha256(self.dataset_path), frozen["sha256"])
        self.assertEqual(len(self.dataset["cases"]), frozen["case_count"])
        self.assertEqual(
            Counter(row["expected_type"] for row in self.dataset["cases"]),
            Counter(frozen["class_counts"]),
        )
        self.assertFalse(frozen["future_holdout_reuse_authorized"])
        self.assertFalse(frozen["official_reflection_label_claim"])
        self.assertFalse(frozen["independent_human_label_validation"])

    def test_fresh_v4_holdout_is_forbidden(self):
        exclusion = self.config["fresh_v4_holdout_exclusion"]
        self.assertFalse(exclusion["may_be_loaded_by_runner"])
        self.assertFalse(exclusion["may_be_used_for_prompt_tuning"])
        self.assertFalse(exclusion["may_be_retested"])
        fresh_text = {
            row["text"].strip().casefold()
            for row in _load(ROOT / exclusion["path"])["cases"]
        }
        development_text = {
            row["text"].strip().casefold() for row in self.dataset["cases"]
        }
        self.assertTrue(fresh_text.isdisjoint(development_text))

    def test_frozen_control_artifacts_and_metrics_are_exact(self):
        control = self.config["frozen_control"]
        self.assertEqual(
            _sha256(ROOT / control["result_lock_path"]),
            control["result_lock_sha256"],
        )
        self.assertEqual(
            _sha256(ROOT / control["analysis_path"]), control["analysis_sha256"]
        )
        analysis = _load(ROOT / control["analysis_path"])["analyses"]["qwen3.5:4b"]
        self.assertEqual(analysis["hybrid_correct_count"], 29)
        self.assertEqual(analysis["hybrid_accuracy"], 0.9062)
        self.assertEqual(control["hybrid_accuracy_reported"], 0.9062)
        self.assertEqual(control["hybrid_accuracy_exact_fraction"], "29/32")
        self.assertEqual(analysis["parse_success_rate"], 1.0)
        self.assertEqual(analysis["critical_false_positive_count"], 0)

    def test_candidate_changes_only_discourse_representation(self):
        candidate = self.config["candidate"]
        self.assertEqual(
            candidate["only_changed_component"],
            "fallback_system_prompt_and_tool_schema_add_explicit_discourse_slots",
        )
        self.assertEqual(
            set(candidate["unchanged_components"]),
            {
                "rules_control",
                "fallback_trigger",
                "dataset",
                "model_and_digest",
                "generation_settings",
                "final_four_label_set",
                "scoring_code_semantics",
            },
        )

    def test_tool_contract_requires_exact_intermediate_slots(self):
        function = self.config["tool_contract"]["function"]
        parameters = function["parameters"]
        expected = set(self.config["candidate"]["discourse_slots"])
        self.assertEqual(set(parameters["properties"]), expected)
        self.assertEqual(set(parameters["required"]), expected)
        self.assertFalse(parameters["additionalProperties"])
        self.assertEqual(
            parameters["properties"]["reflection_type"]["enum"],
            ["semantic", "procedural", "interpretive", "none"],
        )

    def test_prompt_contains_no_case_text_ids_or_gold_labels(self):
        serialized = json.dumps(
            {
                "system_prompt": self.config["system_prompt"],
                "tool_contract": self.config["tool_contract"],
            },
            ensure_ascii=False,
        )
        for row in self.dataset["cases"]:
            self.assertNotIn(row["id"], serialized)
            self.assertNotIn(row["text"], serialized)
        fresh = _load(ROOT / self.config["fresh_v4_holdout_exclusion"]["path"])
        for row in fresh["cases"]:
            self.assertNotIn(row["id"], serialized)
            self.assertNotIn(row["text"], serialized)
        self.assertNotIn("expected_type", serialized)

    def test_theory_basis_uses_primary_sources(self):
        urls = {row["url"] for row in self.config["theory_basis"]}
        self.assertEqual(
            urls,
            {
                "https://www.iso.org/standard/76443.html",
                "https://aclanthology.org/2020.lrec-1.69/",
            },
        )

    def test_success_gates_are_frozen_before_inference(self):
        gates = self.config["success_gates"]
        self.assertEqual(gates["frozen_control_correct_count_exact"], 29)
        self.assertEqual(gates["candidate_correct_count_min"], 31)
        self.assertEqual(gates["newly_correct_vs_frozen_control_min"], 2)
        self.assertEqual(gates["regression_vs_frozen_control_max"], 0)
        self.assertEqual(gates["critical_false_positive_count_max"], 0)
        self.assertEqual(gates["model_call_count_exact"], 20)
        self.assertFalse(self.config["model_inference_before_preregistration_merge_authorized"])
        self.assertFalse(self.config["decision_rule"]["same_dataset_retest_after_result"])
        self.assertFalse(self.config["decision_rule"]["post_result_prompt_or_gate_change"])

    def test_no_runtime_or_broad_claim_is_authorized(self):
        for authorized in self.config["evidence_limits"].values():
            self.assertFalse(authorized)


if __name__ == "__main__":
    unittest.main()
