#!/usr/bin/env python3
"""Validate the frozen V6 evidence-gate development pilot contract."""

from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = (
    ROOT
    / "configs"
    / "reflection_admission_v6_evidence_gate_development_preregistration.json"
)


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ReflectionAdmissionEvidenceGatePreregistrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = _load(CONFIG_PATH)
        cls.dataset_path = ROOT / cls.config["dataset"]["path"]
        cls.dataset = _load(cls.dataset_path)

    def test_dataset_and_construction_closure_are_frozen(self):
        self.assertEqual(
            _sha256(self.dataset_path), self.config["dataset"]["sha256"]
        )
        closure = self.config["construction_closure"]
        self.assertEqual(_sha256(ROOT / closure["path"]), closure["sha256"])
        self.assertEqual(len(self.dataset["cases"]), 32)
        self.assertEqual(
            sum(row["expected_admission"] == "admit" for row in self.dataset["cases"]),
            16,
        )
        self.assertEqual(
            sum(
                row["expected_admission"] == "reject"
                for row in self.dataset["cases"]
            ),
            16,
        )

    def test_control_is_explicit_and_deterministic(self):
        control = self.config["conditions"]["control"]
        self.assertEqual(
            control["name"], "admit_every_proposed_procedural_reflection"
        )
        self.assertEqual(control["model_calls"], 0)
        self.assertEqual(control["expected_correct_count"], 16)
        self.assertEqual(control["expected_accuracy"], 0.5)

    def test_proposal_is_identical_and_narrow(self):
        self.assertTrue(
            self.config["conditions"]["candidate"][
                "proposal_is_identical_for_every_case"
            ]
        )
        self.assertEqual(
            {
                row["proposed_reflection_type"] for row in self.dataset["cases"]
            },
            {"procedural"},
        )
        self.assertEqual(
            self.dataset["proposal_under_review"],
            self.config["proposal_under_review"],
        )

    def test_tool_contract_is_exact_and_has_reject_option(self):
        parameters = self.config["tool_contract"]["function"]["parameters"]
        self.assertEqual(
            set(parameters["properties"]),
            {"admission", "evidence_span", "reason_code"},
        )
        self.assertEqual(set(parameters["required"]), set(parameters["properties"]))
        self.assertFalse(parameters["additionalProperties"])
        self.assertEqual(
            parameters["properties"]["admission"]["enum"], ["admit", "reject"]
        )

    def test_prompt_contains_no_case_text_id_or_gold_label(self):
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
            self.assertNotIn(str(row["source_provenance"]["sentence_id"]), serialized)
        self.assertNotIn("expected_admission", serialized)
        self.assertNotIn("gold_reason", serialized)

    def test_success_gates_require_both_sensitivity_and_specificity(self):
        gates = self.config["success_gates"]
        self.assertEqual(gates["candidate_correct_count_min"], 28)
        self.assertEqual(gates["candidate_admit_correct_min"], 14)
        self.assertEqual(gates["candidate_reject_correct_min"], 14)
        self.assertEqual(gates["false_admit_count_max"], 2)
        self.assertEqual(gates["false_reject_count_max"], 2)
        self.assertEqual(gates["regression_vs_control_max"], 2)
        self.assertEqual(gates["model_call_count_exact"], 32)
        self.assertEqual(gates["parse_success_rate_min"], 1.0)
        self.assertEqual(gates["evidence_contract_success_rate_min"], 1.0)

    def test_model_and_generation_are_local_and_frozen(self):
        self.assertEqual(self.config["model"]["name"], "qwen3.5:4b")
        self.assertEqual(
            self.config["model"]["digest"],
            "2a654d98e6fba55d452b7043684e9b57a947e393bbffa62485a7aac05ee4eefd",
        )
        generation = self.config["generation"]
        self.assertEqual(generation["temperature"], 0.0)
        self.assertFalse(generation["thinking"])
        self.assertTrue(generation["endpoint"].startswith("http://127.0.0.1:"))

    def test_no_runtime_holdout_or_broad_claim_is_authorized(self):
        for value in self.config["evidence_limits"].values():
            self.assertFalse(value)
        self.assertFalse(
            self.config[
                "model_inference_before_preregistration_and_harness_merge_authorized"
            ]
        )
        self.assertFalse(self.config["decision_rule"]["same_dataset_retest_after_result"])
        self.assertFalse(self.config["decision_rule"]["post_result_prompt_or_gate_change"])


if __name__ == "__main__":
    unittest.main()
